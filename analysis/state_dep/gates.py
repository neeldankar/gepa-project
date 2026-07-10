"""APPROVED-gate machinery. Every live-spend script imports and calls `require()` first.

Standing discipline: "APPROVED file: created by Neel only. CC byte-verifies it on disk before any
live spend. No APPROVED, no launch -- no exceptions, including 'just one more run'."

Gates (design v2 §13-7, §14):
    APPROVED-testsplit   ~$1.33   grade ~299 fresh threehop claims -> N=150 imperfect test split
    APPROVED-dose        ~$3.6    30-event determinism control, then the dose re-derivation
    APPROVED-backfill    ~$5.45   8 Stage-1 final candidates x N test evals
    APPROVED-liverun     $50-70   the 24 runs

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
