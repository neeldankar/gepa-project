"""§11-0 dose computation. GATED: APPROVED-dose for the live path (~$3.6).

Two modes run TONIGHT at $0 and need no gate:

  --selftest        validate the order-statistic math (gap definition) on synthetic data
  --pre-estimate    §15-12 degeneracy pre-estimate from the SCREEN's existing 3-member novelty
                    columns in features.csv. Free, and it bounds how much selection room exists.

The live path (--live) needs the 3 unmatched candidates' feedback texts, which do NOT exist on disk
for any of the 243 swap events (see notes/FREEZE.md C1) and must be re-derived by re-executing the
parent. That is real LM spend and is gated.

THE GAP, per review R5(c) and R2 (v2 §11-0):

    For each event, x = the 6 candidates' knn_emb_fb novelties, sorted ASCENDING.

      selected_min = x_(4)          the 4th order statistic ascending
                                    == the 3rd-HIGHEST value
                                    == the min of the top-3-by-novelty subset
                                    == exactly what arm T's selector realizes

      random_min   = (1/20) * sum over all C(6,3)=20 subsets S of min(x_S)
                                    == the expected min of a uniformly random 3-subset
                                    == what arm C realizes in expectation

      gap          = selected_min - random_min

    D_s = mean_{e in seed s} gap_e / sd_s     (each seed in its own within-run SD units)
    D   = mean_s D_s

`sd_s` is the screen's per-run standardization SD (screen_part4_stats.py:62, ddof=0). There is NO
scalar SD_screen: the 8 within-run SDs span [0.021870 .. 0.029460]. Ratified 2026-07-09.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCREEN = os.path.join(REPO, "analysis", "hover_screen")
sys.path.insert(0, HERE)

BETA = 0.0379395028680125  # screen_stats_cells.csv:434, knn_emb_fb_min / spec_i / read 4.1
M, B = 6, 3

# v2.1 §20-2, ratified 2026-07-22: the dose is defined on 235 events, not 243. The 8 ordinal-0
# events have no k=3 archive and no defined novelty, and 235 is the frame BETA above was estimated
# on (verify_novelty.py byte-verified 235/235 against features.csv). Defining D on 243 would put D
# and BETA on different event sets inside the product D x BETA/2 that §11-1 and §11-2 consume.
EVENT_SET = 235

# Per-seed within-run SDs of knn_emb_fb_min (ddof=0), recomputed from features.csv.
SD_PER_SEED = {
    0: 0.02186988, 1: 0.02443303, 2: 0.02946035, 3: 0.02319585,
    4: 0.02871316, 5: 0.02523783, 6: 0.02501051, 7: 0.02653783,
}


def selected_min(x6) -> float:
    """x_(4) ascending == the min of the top-3-by-novelty subset."""
    return float(np.sort(np.asarray(x6, dtype=float))[M - B])


def expected_random_min(x6) -> float:
    """Exact enumeration over all C(6,3)=20 subsets."""
    xs = list(map(float, x6))
    mins = [min(s) for s in itertools.combinations(xs, B)]
    assert len(mins) == 20, len(mins)
    return float(np.mean(mins))


def gap(x6) -> float:
    return selected_min(x6) - expected_random_min(x6)


# --------------------------------------------------------------------------- self-test ($0)
def selftest() -> int:
    print("=== gap() self-test: the order-statistic identity ===")
    rng = np.random.default_rng(20260709)
    ok = True

    # 1. selected_min really is the min of the top-3 subset, and that subset maximizes the min.
    for _ in range(2000):
        x = rng.normal(size=M)
        top3 = np.sort(x)[-B:]
        best = max(min(s) for s in itertools.combinations(map(float, x), B))
        if not (np.isclose(selected_min(x), top3.min()) and np.isclose(selected_min(x), best)):
            ok = False
            print(f"  FAIL on {x}")
            break
    print(f"  selected_min == min(top-3) == max-over-subsets-of-min : {ok}")

    # 2. gap >= 0 always (the selector's min can never be below the average subset min).
    gaps = [gap(rng.normal(size=M)) for _ in range(5000)]
    print(f"  gap >= 0 in all 5000 draws                            : {min(gaps) >= -1e-12}")
    print(f"  mean gap under iid normal                             : {np.mean(gaps):.4f} SD")
    print("    (review R2's ceiling argument: ~1 SD under iid; real novelty scores share an")
    print("     archive and are positively correlated, so the realized D should be well below.)")

    # 3. degenerate case: all six identical -> zero selection room.
    # NB: compare with isclose, not ==. sum(twenty 0.3s)/20 == 0.29999999999999993 in IEEE754, so
    # an exact-equality assertion here fails on a rounding artifact of the TEST, not of gap().
    degenerate = gap([0.3] * 6)
    degenerate_ok = bool(np.isclose(degenerate, 0.0, atol=1e-15))
    print(f"  gap([c]*6) ~= 0 (degenerate, §15-12)                   : {degenerate_ok} "
          f"(gap={degenerate:.3e})")

    # 4. hand-checked example.
    x = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    sm = selected_min(x)  # sorted asc -> index 3 -> 3.0
    rm = expected_random_min(x)
    print(f"  x=0..5 -> selected_min={sm} (expect 3.0), E[rand min]={rm:.4f}, gap={sm - rm:.4f}")
    hand_ok = sm == 3.0 and np.isclose(rm, 0.75)

    ok = bool(ok and degenerate_ok and hand_ok and min(gaps) >= -1e-12)
    print("\nSELFTEST PASS" if ok else "\nSELFTEST FAIL")
    return 0 if ok else 1


# ------------------------------------------------------- degeneracy pre-estimate ($0, real data)
def pre_estimate() -> int:
    """§15-12: how much novelty spread exists within a batch, using the screen's own 3 members.

    This is NOT the dose. The dose needs 6 candidates. But the screen already scored the 3 reflected
    members per event, so the within-event spread over those 3 is a free lower-bound-ish read on
    whether there is anything to select on at all. If the 3-member spread were ~0, the 6-member
    spread would likely be small too and T ~= C by construction.
    """
    rows = list(csv.DictReader(open(os.path.join(SCREEN, "features.csv"))))
    per_seed = {}
    for r in rows:
        if r["knn_emb_fb_min"] == "":
            continue  # ordinal-0, no k=3 archive
        s = int(r["seed"])
        lo, hi = float(r["knn_emb_fb_min"]), float(r["knn_emb_fb_max"])
        sd = float(r["knn_emb_fb_std"])
        per_seed.setdefault(s, []).append((hi - lo, sd, float(r["knn_emb_fb_mean"])))

    print("=== §15-12 degeneracy pre-estimate (3 reflected members per event; NOT the dose) ===")
    print(f"{'seed':>5} {'n':>4} {'mean spread':>13} {'spread/sd_s':>13} {'mean within-ev sd':>19}")
    all_norm = []
    for s in sorted(per_seed):
        v = per_seed[s]
        spread = np.mean([a for a, _, _ in v])
        wsd = np.mean([b for _, b, _ in v])
        norm = spread / SD_PER_SEED[s]
        all_norm.append(norm)
        print(f"{s:>5} {len(v):>4} {spread:>13.6f} {norm:>13.4f} {wsd:>19.6f}")
    print(f"\n  pooled mean (max-min) spread over 3 members, in within-run SD units: "
          f"{np.mean(all_norm):.4f} SD")
    print("  Reading: there IS selection room -- the within-event spread across just 3 members is")
    print("  of the same order as the between-event SD the screen's beta is denominated in. With 6")
    print("  candidates the spread can only grow. This does not estimate D; it rules out the")
    print("  degenerate case where T == C by construction.")
    return 0


# --------------------------------------------------------------------------- the live path
def live() -> int:
    from gates import require

    gate = require("APPROVED-dose")
    raise SystemExit(
        "\nNOT IMPLEMENTED BEYOND THE GATE.\n"
        "Requires, per v2 §11-0, in order:\n"
        "  1. dose_control.py: 30-event determinism control, 30/30 byte-exact, else STOP.\n"
        "  2. re-derive the 3 unmatched candidates' feedback per event by re-executing the parent\n"
        "     (temp-0 task LM, capture_traces=True, identical make_reflective_dataset path).\n"
        "  3. parse the 3 matched B_e texts out of reflect_in_SWAP.txt.\n"
        "  4. score all 6 against the screen's archive state for that event (novelty.py).\n"
        "  5. gap_e per event; D_s per seed; D = mean(D_s).\n"
        f"Event set: {EVENT_SET} events (v2.1 §20-2, ratified 2026-07-22 -- ordinal-0 excluded, the\n"
        f"frame beta was estimated on). Re-derivation {3 * EVENT_SET} calls + 90 control calls\n"
        f"= {3 * EVENT_SET + 90} x $0.004543 = ${(3 * EVENT_SET + 90) * 0.004543:.2f}.\n"
        "This path is OFF the launch critical path under v2.1 §11-2's amended gate timing: it must\n"
        "clear before results.md is read, not before APPROVED-liverun.\n"
        f"Gate verified: {gate['sha256'][:16]}...\n"
    )


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pre-estimate", action="store_true")
    ap.add_argument("--live", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    if a.pre_estimate:
        raise SystemExit(pre_estimate())
    if a.live:
        raise SystemExit(live())
    ap.error("pick one of --selftest / --pre-estimate / --live")
