"""§8a Stage-1 backfill: evaluate the 8 Stage-1 final candidates on the test split.

GATED: APPROVED-backfill (~$5.45 at N=150). Also requires the split to exist
(APPROVED-testsplit -> build_test_split.py).

Produces the empirical endpoint distribution that §11-2's MDE simulation draws from. Without it
there is no MDE, and plan.md carries a placeholder.

The "final candidate" per seed is defined by the §8 selection convention, which is gepa's own
(V5, verified):

    best_idx = max(range(len(agg)), key=lambda i: agg[i])     # core/result.py:82-88
    agg[i]   = mean(prog_candidate_val_subscores[i].values())

Python's `max` returns the FIRST maximal element and `range` ascends, so ties go to the LOWEST
index = the earliest-accepted candidate. Note the persisted `gepa_result.json` is a custom
state_dump WITHOUT `val_aggregate_scores`/`best_idx` (v2 §12 note, B8): the endpoint is recomputed
from `prog_candidate_val_subscores`.

  --resolve   ($0, runs tonight)  identify the 8 final candidates and print their val scores
  --run       (gated)             evaluate them on the test split
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
STAGE1 = os.path.join(REPO, "scratch", "hover_stage1")
SPLIT = os.path.join(HERE, "test_split.json")
OUT = os.path.join(HERE, "stage1_backfill_endpoints.json")

sys.path.insert(0, HERE)


def final_candidate(seed: int) -> dict:
    g = json.load(open(os.path.join(STAGE1, f"stage1_seed{seed}", "gepa_result.json")))
    subs = g["prog_candidate_val_subscores"]
    agg = [sum(d.values()) / len(d) if d else float("-inf") for d in subs]
    best = max(range(len(agg)), key=lambda i: agg[i])  # ties -> lowest index (V5)
    ties = [i for i, v in enumerate(agg) if v == agg[best]]
    return {
        "seed": seed,
        "n_candidates": len(subs),
        "best_idx": best,
        "best_val_agg": agg[best],
        "tied_indices": ties,
        "tie_broken": len(ties) > 1,
        "coverage": [len(d) for d in subs],
        "instruction": g["program_candidates"][best],
    }


def resolve() -> int:
    print("=== Stage-1 final candidates (v2 §8 convention: val-argmax, ties -> lowest index) ===")
    print(f"{'seed':>5} {'ncand':>6} {'best_idx':>9} {'val_agg':>9} {'tied':>18}")
    rows = []
    for s in range(8):
        r = final_candidate(s)
        rows.append(r)
        print(f"{s:>5} {r['n_candidates']:>6} {r['best_idx']:>9} {r['best_val_agg']:>9.4f} "
              f"{str(r['tied_indices']):>18}{'  <- TIE' if r['tie_broken'] else ''}")
    n_tie = sum(r["tie_broken"] for r in rows)
    print(f"\n  seeds where the tie-break actually fired: {n_tie}/8")
    print("  (a tie means two candidates share the top mean val score; the earliest-accepted wins)")
    print("\n  These 8 candidates are what APPROVED-backfill evaluates on the §8a test split.")
    print(f"  Estimated cost: 8 x N x $0.004543  =>  N=150: $5.45   N=100: $3.63")
    return 0


def run_live() -> int:
    from gates import require

    gate = require("APPROVED-backfill")
    if not os.path.exists(SPLIT):
        print(f"missing {SPLIT}: run build_test_split.py behind APPROVED-testsplit first")
        return 1
    raise SystemExit(
        "\nNOT IMPLEMENTED BEYOND THE GATE.\n"
        "Evaluate each of the 8 resolved candidates on the committed test split with the SAME\n"
        "program/retrieval/metric as Stage 1 (probe venv), post-hoc and outside any budget, then\n"
        f"write the 8 endpoint scores to {os.path.basename(OUT)} for mde_sim.py --endpoints.\n"
        f"Gate verified: {gate['sha256'][:16]}...\n"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--run", action="store_true")
    a = ap.parse_args()
    if a.resolve:
        raise SystemExit(resolve())
    if a.run:
        raise SystemExit(run_live())
    ap.error("pick --resolve ($0) or --run (gated)")
