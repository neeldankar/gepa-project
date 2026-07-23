"""APPROVED-gate machinery. Every live-spend script imports and calls `require()` first.

Standing discipline: "APPROVED file: created by Neel only. CC byte-verifies it on disk before any
live spend. No APPROVED, no launch -- no exceptions, including 'just one more run'."

Gates (design v2.1 §13-7, §14 -- re-derived 2026-07-22 for the §8b selection split):
    APPROVED-testsplit   ~$3.13    grade a fixed 700-claim frame -> test (150) + selection (50)
    APPROVED-dose        ~$3.61    30-event determinism control, then 235-event re-derivation
    APPROVED-backfill    ~$27.49   97 Stage-1 candidates x 50 selection + 8 winners x 150 test
    APPROVED-liverun     ~$130-180 live smoke + 24 runs + the §8b post-run selection pass

The backfill and liverun numbers are NOT the pre-amendment ones. §8b evaluates every candidate in
every pool on a 50-claim split, which no earlier cost model carried: the backfill went $5.45 ->
$27.49 (97 candidates is a realized count, not an estimate) and the program total ~$60-80 ->
~$165-215. Scripts print their own arithmetic before asking for the gate.

Scripts holding these gates:
    APPROVED-testsplit   build_test_split.py
    APPROVED-dose        dose_control.py --run, dose_compute.py --live
    APPROVED-backfill    backfill_stage1.py --run
    APPROVED-liverun     run_state_dep.py, score_candidates.py, supervisor.py

CC MUST NOT create these files (standing do-not list).
"""
from __future__ import annotations

import hashlib
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GATE_DIR = os.path.join(REPO, "analysis", "state_dep")

KNOWN_GATES = ("APPROVED-testsplit", "APPROVED-dose", "APPROVED-backfill", "APPROVED-liverun")


def require(gate: str) -> dict:
    """Byte-verify the gate file on disk. Exits non-zero if absent. Returns its provenance record."""
    assert gate in KNOWN_GATES, f"unknown gate {gate!r}; expected one of {KNOWN_GATES}"
    path = os.path.join(GATE_DIR, gate)
    if not os.path.exists(path):
        print(f"\nGATE MISSING: {path}")
        print("This script performs LIVE API SPEND and will not run without it.")
        print("The gate file is created by Neel only. CC must never create it.")
        sys.exit(2)
    with open(path, "rb") as fh:
        body = fh.read()
    rec = {
        "gate": gate,
        "path": path,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
    }
    print(f"[gate ok] {gate}  bytes={rec['bytes']}  sha256={rec['sha256'][:16]}...")
    return rec


def forbid_if_dry(dry: bool, what: str) -> None:
    if dry:
        print(f"[dry-run] would now perform: {what}")
