"""ACCEPTANCE GATE (design v2 §5, §13-2): byte-verify the re-implemented novelty scorer.

Recomputes `knn_emb_fb_min` for every screen event from the raw pair bytes, using
analysis/state_dep/novelty.py, and compares against the committed
analysis/hover_screen/features.csv.

PASS  <=> all 235 non-NaN events match to < 1e-12  AND  the 8 NaN events are still NaN.
FAIL  => STOP. A mismatch is a silent-proxy-substitution incident (v2 §5).

$0: no API calls. Loads the local pinned embedding snapshot only.
Read-only: touches nothing under analysis/hover_screen/ or analysis/ablation/hover_swap/.

Run:  analysis/state_dep/.venv-armT/bin/python analysis/state_dep/verify_novelty.py
"""
from __future__ import annotations

import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCREEN = os.path.join(REPO, "analysis", "hover_screen")
PAIRS = os.path.join(REPO, "analysis", "ablation", "hover_swap", "pairs")

sys.path.insert(0, HERE)
sys.path.insert(0, SCREEN)  # screen_part0 is import-clean (constants + functions, guarded main)

from novelty import (  # noqa: E402
    batch_min,
    encode,
    feedback_text,
    full_text,
    knn_novelty,
    load_embedder,
    verify_weights_on_disk,
)
from screen_part0 import parse_si  # noqa: E402  (read-only import; no side effects)

TOL = 1e-12


def main() -> int:
    print("=== weights pin ===")
    w = verify_weights_on_disk()
    print(f"  {w['path']}")
    print(f"  sha256 {w['sha256']}  ok={w['sha256_ok']}")
    print(f"  bytes  {w['bytes']}  ok={w['bytes_ok']}")
    if not (w["sha256_ok"] and w["bytes_ok"]):
        print("\nGATE FAIL: embedding weights on disk do not match the v2 §0 pin.")
        return 1

    # ---- parse every SAME-arm reflection object, in the screen's own pid order (:111-114)
    blocks_by_pid = {}
    for pid in sorted(os.listdir(PAIRS)):
        text = open(os.path.join(PAIRS, pid, "reflect_in_SAME.txt"), encoding="utf-8").read()
        blocks_by_pid[pid] = parse_si(text, pid)
    print(f"\n=== parsed {len(blocks_by_pid)} pair dirs ===")
    nblk = {len(b) for b in blocks_by_pid.values()}
    print(f"  blocks per pid: {nblk}  (screen asserts 3)")
    if nblk != {3}:
        print("GATE FAIL: unexpected block count")
        return 1

    # ---- encode EXACTLY as the screen does (:123-130): one call, interleaved (fb, full),
    # batch_size=64, normalize_embeddings=True. sentence_transformers sorts by length internally,
    # so batch composition matters; we reproduce the whole text list, not just the fb texts.
    model = load_embedder()
    keys, texts = [], []
    for pid, blks in blocks_by_pid.items():
        for j, blk in enumerate(blks):
            keys += [(pid, j, "fb"), (pid, j, "full")]
            texts += [feedback_text(blk), full_text(blk)]
    M = encode(model, texts)
    emb = {k: M[i] for i, k in enumerate(keys)}
    print(f"=== embedded {len(texts)} block texts, dim {M.shape[1]} ===")

    # ---- per-seed chronological loop, archive advanced STRICTLY AFTER the event (:135-340)
    ev_index = json.load(open(os.path.join(SCREEN, "events_index.json")))
    got = {}
    for seed in range(8):
        evs = sorted(
            [e for e in ev_index.values() if e["seed"] == seed], key=lambda e: e["ordinal"]
        )
        arch_emb: list[np.ndarray] = []
        for ev in evs:
            pid = f"seed{seed}_i{ev['trace_i']}"
            blks = blocks_by_pid[pid]

            n_arch = len(arch_emb)  # snapshot BEFORE this event's members are added (:203)
            per_member = [
                knn_novelty(emb[(pid, slot, "fb")], arch_emb if n_arch >= 3 else None)
                for slot in range(len(blks))
            ]
            got[pid] = batch_min(per_member)

            # advance archive strictly after scoring (:327-338)
            for slot in range(len(blks)):
                arch_emb.append(emb[(pid, slot, "fb")])

    # ---- compare to the committed features.csv
    rows = list(csv.DictReader(open(os.path.join(SCREEN, "features.csv"))))
    n_cmp = n_nan = 0
    worst = 0.0
    worst_pid = None
    failures = []
    for r in rows:
        pid = r["pair_id"]
        want_raw = r["knn_emb_fb_min"]
        mine = got[pid]
        if want_raw == "":
            n_nan += 1
            if not np.isnan(mine):
                failures.append((pid, "expected NaN", mine))
            continue
        want = float(want_raw)
        d = abs(want - mine)
        n_cmp += 1
        if d > worst:
            worst, worst_pid = d, pid
        if d > TOL:
            failures.append((pid, want, mine))

    print("\n=== comparison vs analysis/hover_screen/features.csv ===")
    print(f"  events compared (non-NaN) : {n_cmp}   (expect 235)")
    print(f"  events NaN in both        : {n_nan}   (expect 8, all ordinal-0)")
    print(f"  max abs diff              : {worst:.3e}   at {worst_pid}")
    print(f"  tolerance                 : {TOL:.0e}")

    if failures:
        print(f"\nGATE FAIL: {len(failures)} mismatches. First 10:")
        for f in failures[:10]:
            print(f"    {f}")
        return 1
    if n_cmp != 235 or n_nan != 8:
        print(f"\nGATE FAIL: coverage mismatch (got {n_cmp} non-NaN / {n_nan} NaN)")
        return 1

    print("\nGATE PASS: re-implemented knn_emb_fb_min reproduces the frozen screen")
    print(f"           on all {n_cmp} scored events to < {TOL:.0e}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
