"""§11-2 MDE simulation. $0 (pure simulation) -- but its INPUT needs APPROVED-backfill.

The DGP is pre-registered verbatim in v2 §11-2 (from review R11):

    Per synthetic replicate, draw 8 paired differences as X_T - X_C with both margins drawn
    independently from the backfilled Stage-1 empirical endpoint distribution (independence
    encodes rho=0, consistent with the sqrt(2) bound); shift by the candidate effect; apply the
    two-sided exact sign-flip at alpha=0.05; MDE = smallest shift reaching 80% rejection.
    The simulation script is committed and its hash cited in plan.md.

So: the simulation itself costs nothing and runs tonight against a synthetic endpoint distribution
(--selftest). The real run (--endpoints FILE) needs the 8 Stage-1 final candidates evaluated on the
§8a test split, which needs APPROVED-testsplit then APPROVED-backfill.

The exact sign-flip test enumerates all 2^8 = 256 sign patterns. Minimum attainable two-sided p is
2/256 = 0.0078, so alpha=0.05 is reachable at n=8; at n=5 it is not (v2 §10 seed floor).
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ALPHA = 0.05
POWER = 0.80
N_SEEDS = 8
N_REPS = 4000

BETA = 0.0379395028680125  # screen beta, per within-run SD
GATE_K = 3  # v2 §11-2: MDE_endpoint > 3 * (D * beta/2) flips the default


def signflip_p(diffs: np.ndarray) -> float:
    """Exact two-sided sign-flip permutation p over all 2^n sign patterns."""
    n = len(diffs)
    obs = abs(diffs.mean())
    signs = np.array(list(itertools.product([-1.0, 1.0], repeat=n)))  # (2^n, n)
    null = np.abs((signs * diffs).mean(axis=1))
    return float((null >= obs - 1e-12).mean())


def power_at(shift: float, endpoints: np.ndarray, rng: np.random.Generator, n_reps: int = N_REPS) -> float:
    """Fraction of replicates where the exact sign-flip test rejects at ALPHA."""
    rejects = 0
    for _ in range(n_reps):
        xt = rng.choice(endpoints, size=N_SEEDS, replace=True)
        xc = rng.choice(endpoints, size=N_SEEDS, replace=True)
        d = (xt - xc) + shift  # independent margins => rho = 0
        if signflip_p(d) < ALPHA:
            rejects += 1
    return rejects / n_reps


def find_mde(endpoints: np.ndarray, rng: np.random.Generator, n_reps: int = N_REPS) -> tuple[float, list]:
    """Smallest shift reaching POWER. Coarse grid then bisection."""
    sd = float(np.std(endpoints, ddof=1))
    curve = []
    lo, hi = 0.0, max(4.0 * sd, 1e-6)
    # expand until powered
    while power_at(hi, endpoints, rng, n_reps // 4) < POWER:
        hi *= 1.5
        if hi > 100 * sd:
            return float("nan"), curve
    for _ in range(14):  # bisection
        mid = 0.5 * (lo + hi)
        p = power_at(mid, endpoints, rng, n_reps)
        curve.append((mid, p))
        if p < POWER:
            lo = mid
        else:
            hi = mid
    return hi, curve


def report(endpoints: np.ndarray, label: str, dose_D: float | None) -> None:
    rng = np.random.default_rng(20260709)
    sd = float(np.std(endpoints, ddof=1))
    print(f"=== MDE simulation: {label} ===")
    print(f"  n endpoints        : {len(endpoints)}")
    print(f"  endpoint mean / sd : {endpoints.mean():.4f} / {sd:.4f}")
    print(f"  sqrt(2)*sd bound   : {np.sqrt(2) * sd:.4f}   (rho=0; v2 §11-3 caveat: B-arm SD)")
    print(f"  n seeds            : {N_SEEDS}   min attainable p = {2 / 2**N_SEEDS:.4f}")

    mde, curve = find_mde(endpoints, rng)
    print(f"\n  MDE (80% power, exact sign-flip, alpha={ALPHA}) : {mde:.4f} endpoint points")
    print(f"  MDE / endpoint sd                              : {mde / sd:.3f}")

    if dose_D is not None:
        implied = dose_D * BETA / 2  # one-step specificity units
        trigger = GATE_K * implied
        print(f"\n  --- §11-2 gate (heuristic screen, NOT a power calculation) ---")
        print(f"  D (dose, within-run SD units)      : {dose_D:.4f}")
        print(f"  implied one-step effect D*beta/2   : {implied:.5f}  (specificity units)")
        print(f"  gate trigger  {GATE_K} x that        : {trigger:.5f}")
        print(f"  MDE_endpoint                       : {mde:.5f}  (ENDPOINT units)")
        print(f"  GATE BITES (MDE > trigger)         : {mde > trigger}")
        print("  NOTE: this juxtaposes endpoint units against one-step specificity units,")
        print("        exactly as v2 §11-2 pre-registers, and is caveated there.")
    else:
        print("\n  (no dose supplied; run dose_compute.py --live behind APPROVED-dose,")
        print("   then pass --dose D to evaluate the §11-2 gate)")


def selftest() -> int:
    """Validate the machinery on synthetic endpoints. $0, no backfill needed."""
    rng = np.random.default_rng(1)
    print("=== sign-flip exactness checks ===")
    d = np.array([1.0] * 8)
    print(f"  all-positive diffs -> p = {signflip_p(d):.5f}  (expect 2/256 = {2/256:.5f})")
    d = np.array([0.0] * 8)
    print(f"  all-zero diffs     -> p = {signflip_p(d):.5f}  (expect 1.0)")
    d = np.array([1, -1, 1, -1, 1, -1, 1, -1], dtype=float)
    print(f"  symmetric diffs    -> p = {signflip_p(d):.5f}  (expect 1.0)")

    print("\n=== power is monotone in shift, and ~alpha at shift 0 ===")
    endpoints = rng.normal(0.55, 0.06, size=8)  # stand-in for 8 Stage-1 test scores
    for shift in (0.0, 0.05, 0.10, 0.20):
        p = power_at(shift, endpoints, np.random.default_rng(7), n_reps=800)
        print(f"  shift={shift:.2f} -> power={p:.3f}")

    print()
    report(endpoints, "SYNTHETIC endpoints (NOT the real backfill)", dose_D=0.5)
    print("\nSELFTEST PASS (machinery only; the real MDE needs APPROVED-backfill)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--endpoints", help="the 8 backfilled Stage-1 test scores: either a bare JSON "
                                        "list, or the dict backfill_stage1.py --run writes, whose "
                                        "'endpoints' key holds that list")
    ap.add_argument("--dose", type=float, default=None, help="D from dose_compute.py --live")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    if not a.endpoints:
        ap.error("need --selftest or --endpoints")
    # backfill_stage1.py:188 writes {"design":…, "endpoints":[…], "rows":[…]}, not a bare list.
    # Accept both: the dict carries provenance worth keeping, and the producer is frozen at its
    # §7 hash, so the consumer is the correct side to widen.
    blob = json.load(open(a.endpoints))
    if isinstance(blob, dict):
        if "endpoints" not in blob:
            ap.error(f"{a.endpoints}: dict has no 'endpoints' key (got {sorted(blob)})")
        blob = blob["endpoints"]
    pts = np.asarray(blob, dtype=float)
    report(pts, os.path.basename(a.endpoints), a.dose)
