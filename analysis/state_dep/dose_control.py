"""§11-0 reproducibility control for the dose. GATED: APPROVED-dose for the live half (~$2.0).

WHAT THIS CONTROL ASKS, UNDER v2.2:

    A seeded sample (random.Random(20260709)) of 30 events: re-derive all 6 candidates' feedback
    TWICE in one session, compute D_30 on each pass, and require
        |D_30(pass 1) - D_30(pass 2)| <= mean(D_30)
    i.e. the noise must not exceed the signal. Fail -> STOP, and drop the dose.

WHAT IT ASKED UNDER v2.1, AND WHY THAT CHANGED. The old bar was 90/90 byte-exact against the
texts persisted on 2026-07-09. That made sense only while the dose MIXED 3 persisted texts with 3
re-derived ones and needed a licence for the mix. v2.2 re-derives all 6 from one execution, so
nothing is compared to the old run and the question is moot.

It was also unanswerable. `hover_swap_run.py:160` builds the task LM with no `temperature`, so
dspy's default 0.0 applies and `cache=False` means nothing is replayed -- but temp-0 is not a
bitwise contract at the API level, and three same-venv re-executions already on disk
(pairs/, pairs_pre_mmap/, pairs_mmap_check/) reproduce only 15/24 feedback blocks. P(90/90) is
about 4e-19. The old control could only ever have returned STOP.

The replacement measures the thing that actually threatens D: D is a difference of order
statistics over 6 noisy novelties, so it is meaningful only if it exceeds the re-execution noise
of the very program that produces it. That is measured here, on the actual dose data.

TWO PHASES.

  --freeze-expected   ($0, no gate)  [SUPERSEDED, retained]
      Drew the 30 events and committed the sha256s of their persisted B_e blocks to
      dose_control_expected.json on 2026-07-09. Still the source of the 30-event SAMPLE, which is
      NOT re-drawn -- re-drawing it now would be exactly the tampering the control precludes. Its
      90 hashes are no longer the acceptance criterion.

  --run               (live, requires APPROVED-dose)
      Acquire 30 x 6 x 2 under the swap's own venv, score both passes, apply the bar above, and
      write markers/DOSE_CONTROL.PASS only if it clears.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCREEN = os.path.join(REPO, "analysis", "hover_screen")
PAIRS = os.path.join(REPO, "analysis", "ablation", "hover_swap", "pairs")
EXPECTED = os.path.join(HERE, "dose_control_expected.json")
MARKERS = os.path.join(HERE, "markers")
PASS_MARKER = os.path.join(MARKERS, "DOSE_CONTROL.PASS")
CONTROL_TEXTS = os.path.join(HERE, "dose_control_texts")
CONTROL_RESULT = os.path.join(HERE, "dose_control_result.json")
CONTROL_CAP = 2.50   # 30 events x 6 candidates x 2 passes = 360 metric calls

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


def sha256_of(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def write_pass_marker(n_events: int, n_blocks: int, expected_sha: str) -> None:
    """Record a CLEARED reproducibility control. dose_compute.py --live REFUSES without this file.

    CALL THIS ONLY WHEN THE BAR IS MET. The pre-registered response to a failed control is to
    DROP the dose (§11-0) -- never to write this marker with a caveat, never to retune the bar
    after seeing the numbers, and never the biased 3-candidate shrink. There is deliberately no
    "partial pass" field for a caller to rationalize around: the marker exists, or the dose does
    not happen.
    """
    os.makedirs(MARKERS, exist_ok=True)
    with open(PASS_MARKER, "w") as fh:
        json.dump({
            "control": "within-session reproducibility of D over two independent re-derivations",
            "design": "state-dependent-design-v2.2-frozen §11-0",
            "bar": "|D_30(pass1) - D_30(pass2)| <= mean(D_30)",
            "control_seed": CONTROL_SEED,
            "n_events": n_events,
            "n_blocks_compared": n_blocks,
            "superseded_expected_file_sha256": expected_sha,
            "note": "v2.1's 90/90 byte-exact bar is superseded; its frozen hashes remain on disk "
                    "as the record of that design. See dose_control_result.json for the numbers.",
        }, fh, indent=2)


def run_live() -> int:
    """v2.2 control: re-derive 30 events TWICE in one session and compare the two D_30 estimates.

    WHAT CHANGED AND WHY. v2.1 asked a different question -- does today's re-execution reproduce
    2026-07-09's bytes exactly, 90/90, else STOP -- because the dose then MIXED 3 persisted texts
    with 3 re-derived ones and needed a licence for the mix. That question is now moot (v2.2
    re-derives all 6, so nothing is compared to the old run) and it was also unanswerable: three
    same-venv re-executions already on disk reproduce only 15/24 blocks, so P(90/90) ~ 4e-19.

    The question that matters for a dose is different: D is a difference of order statistics, so
    it is only meaningful if it is larger than this program's own re-execution noise. So the
    control now measures exactly that, on the actual dose data, and applies a bar chosen BEFORE
    any result exists:

        STOP if |D_30(pass 1) - D_30(pass 2)| > mean(D_30)

    i.e. stop if the noise is bigger than the signal. dose_control_expected.json's 90 frozen
    hashes stay on disk as the record of the superseded design; they are no longer consulted.
    """
    from gates import require

    gate = require("APPROVED-dose")
    if not os.path.exists(EXPECTED):
        print(f"missing {EXPECTED}; run --freeze-expected first (it is $0)")
        return 1
    exp = json.load(open(EXPECTED))
    pids = sorted(exp["events"])

    import dose_compute as dc

    print(f"=== dose reproducibility control (v2.2): {len(pids)} events x 6 x 2 passes ===")
    print(f"  sample     : frozen 2026-07-09, seed {CONTROL_SEED} (unchanged -- not re-drawn)")
    print(f"  acquisition: {os.path.relpath(dc.PROBE_PY, REPO)}")
    print(f"  bar        : |D_30(1) - D_30(2)| <= mean(D_30)")
    print(f"  gate       : {gate['sha256'][:16]}...\n")

    rc = subprocess.call([dc.PROBE_PY, "-u", dc.ACQUIRE, "--pids", ",".join(pids),
                          "--out", CONTROL_TEXTS, "--passes", "2", "--cap", str(CONTROL_CAP)],
                         cwd=REPO)
    if rc != 0:
        print(f"\nacquisition failed (rc={rc}); checkpoints kept, re-running resumes at $0")
        return rc

    print("\n=== scoring both passes (.venv-armT, $0) ===")
    r1 = dc.score_texts(CONTROL_TEXTS, which_pass=0)
    r2 = dc.score_texts(CONTROL_TEXTS, which_pass=1)
    d1, d2 = r1["D"], r2["D"]
    mean_d, delta = (d1 + d2) / 2.0, abs(d1 - d2)

    # descriptive only: how often did the two passes render byte-identical text?
    same = tot = 0
    for fn in sorted(os.listdir(CONTROL_TEXTS)):
        if not fn.endswith(".json"):
            continue
        rec = json.load(open(os.path.join(CONTROL_TEXTS, fn)))
        for pos, t1 in rec["passes"][0].items():
            tot += 1
            same += (t1 == rec["passes"][1][pos])

    print(f"  D_30 pass 1 : {d1:.4f}   ({r1['n_events']} events)")
    print(f"  D_30 pass 2 : {d2:.4f}   ({r2['n_events']} events)")
    print(f"  |delta|     : {delta:.4f}    mean : {mean_d:.4f}")
    print(f"  byte-identical blocks across passes : {same}/{tot} "
          f"({100.0 * same / max(1, tot):.1f}%)  [descriptive]")

    result = {"design": "state-dependent-design-v2.2-frozen §11-0", "n_events": len(pids),
              "D_pass1": d1, "D_pass2": d2, "abs_delta": delta, "mean_D": mean_d,
              "bar": "|D1 - D2| <= mean(D)", "passed": bool(delta <= mean_d),
              "byte_identical_blocks": [same, tot]}
    json.dump(result, open(CONTROL_RESULT, "w"), indent=2)

    if delta > mean_d:
        print(f"\nCONTROL FAILED: noise ({delta:.4f}) exceeds signal ({mean_d:.4f}).")
        print("Pre-registered response (§11-0): DROP THE DOSE. Do not write the marker, do not")
        print("retune the bar, and NEVER substitute the biased 3-candidate shrink -- B_idx was")
        print("SELECTED to match the parent's score profile on A_e, so it is not a uniform")
        print("3-subset of the 6. results.md then carries the estimation-only framing.")
        return 1

    write_pass_marker(len(pids), tot, sha256_of(EXPECTED))
    print(f"\nCONTROL PASSED. Wrote {os.path.relpath(PASS_MARKER, HERE)}.")
    print("  next: dose_compute.py --live  (now unblocked)")
    return 0


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
