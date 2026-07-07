"""Task 1 — independent reproduction of the sibling-ranking probe ($0, reads calls.csv).

Definitions (from cc-brief-postswap-verification.md, Task 1):
  arm-cell = (pair, arm); 382 pairs x 2 arms = 764 cells, 3 draws each.
  own-margin  = margin_on_B for R_B, margin_on_Bp for R_Bp.
  other-margin= the non-reflected batch's margin.
  accept      = own-margin > 0.
  best-of-3   = draws with max own-margin (ties averaged).
  selection lift = mean over cells of [mean other-margin of selected - mean other-margin of all 3].
  within-cell corr = demean own/other within each cell, pool all 2292 points, Pearson.
  cluster boot on selection lift: resample the 8 runs (seed prefix of B_id), 4000 iters, pct 95%.

    HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/verify_task1_sibling_probe.py
"""
from __future__ import annotations

import collections
import csv

import numpy as np

OUT = "analysis/ablation/batch_swap_v2"
BOOT = 4000
rng = np.random.default_rng(20260705)


def own_other(r, arm):
    mB, mBp = float(r["margin_on_B"]), float(r["margin_on_Bp"])
    return (mB, mBp) if arm == "R_B" else (mBp, mB)


def own_other_child(r, arm):
    """own/other by child_sum (own-batch child_sum) — for a robustness selection variant."""
    cB, cBp = float(r["child_sum_B"]), float(r["child_sum_Bp"])
    # other-margin stays the margin criterion (held-out quantity); only the SELECTION key changes
    own_c = cB if arm == "R_B" else cBp
    mB, mBp = float(r["margin_on_B"]), float(r["margin_on_Bp"])
    other_m = mBp if arm == "R_B" else mB
    return own_c, other_m


def cells(rows):
    by = collections.defaultdict(list)
    for r in rows:
        by[(r["B_id"], r["arm"])].append(r)
    return by


def selection_lift(by, select_key, tol=None):
    """mean over cells of (mean other-margin of selected - mean other-margin of all 3).
    select_key(r,arm) -> selection scalar; own/other margins via own_other.
    tol: if not None, selected = draws within tol of max (tie-tolerant); else exact argmax(es)."""
    lifts, run = [], []
    for (pid, arm), rs in by.items():
        keys = np.array([select_key(r, arm) for r in rs])
        others = np.array([own_other(r, arm)[1] for r in rs])
        mx = keys.max()
        if tol is None:
            sel = keys == mx
        else:
            sel = keys >= mx - tol
        sel_other = others[sel].mean()
        all_other = others.mean()
        lifts.append(sel_other - all_other)
        run.append(pid.split("_")[0])
    return np.array(lifts), np.array(run)


def cluster_boot(x, run):
    uniq = np.unique(run)
    by = {c: x[run == c] for c in uniq}
    means = [np.concatenate([by[c] for c in rng.choice(uniq, len(uniq), replace=True)]).mean()
             for _ in range(BOOT)]
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def m(name, got, ref):
    v = "MATCH" if round(got, 4) == round(ref, 4) else "MISMATCH"
    print(f"  {name}: got={got:+.4f} ref={ref:+.4f} -> {v}")


def main():
    rows = list(csv.DictReader(open(f"{OUT}/calls.csv")))
    by = cells(rows)
    print(f"cells={len(by)}  draws={len(rows)}")

    owns = np.array([own_other(r, r["arm"])[0] for r in rows])
    others = np.array([own_other(r, r["arm"])[1] for r in rows])

    # single-draw accept rate + E[own]
    single_acc = float((owns > 0).mean())
    e_own_single = float(owns.mean())

    # best-of-3: within each cell, selected = argmax own-margin (ties averaged)
    bo3_acc, bo3_own = [], []
    for (pid, arm), rs in by.items():
        o = np.array([own_other(r, arm)[0] for r in rs])
        mx = o.max()
        sel = o == mx
        bo3_own.append(o[sel].mean())          # mean own-margin of selected (ties averaged)
        bo3_acc.append(1.0 if mx > 0 else 0.0)  # accept if best own-margin > 0
    bo3_acc = float(np.mean(bo3_acc))
    bo3_own = float(np.mean(bo3_own))

    # selection lift (main): select by own-margin, ties averaged
    lift, run = selection_lift(by, lambda r, arm: own_other(r, arm)[0])
    lift_pt = float(lift.mean())
    lo, hi = cluster_boot(lift, run)

    # within-cell correlation: demean own/other within cell, pool, Pearson
    du, do = [], []
    for (pid, arm), rs in by.items():
        o = np.array([own_other(r, arm)[0] for r in rs])
        t = np.array([own_other(r, arm)[1] for r in rs])
        du.extend(o - o.mean())
        do.extend(t - t.mean())
    du, do = np.array(du), np.array(do)
    corr = float(np.corrcoef(du, do)[0, 1])

    print("\n== Task 1 reference checks ==")
    m("single-draw accept rate", single_acc, 0.3443)
    m("best-of-3 accept rate", bo3_acc, 0.5641)
    m("E[own-margin] single", e_own_single, 0.0043)
    m("E[own-margin] best-of-3 selected", bo3_own, 0.2298)
    m("selection lift", lift_pt, 0.0059)
    print(f"  selection lift CI: got=[{lo:+.4f},{hi:+.4f}] ref=[-0.0057,+0.0199]")
    m("within-cell correlation", corr, 0.0010)

    # ---- robustness rows (no reference) ----
    # (A) accept>=0 tie-tolerant: "selected" = all siblings with own-margin >= 0 (the accept set),
    #     ties averaged; cells where no draw accepts (own-margin>=0) are skipped.
    liftA, runA, skipped = [], [], 0
    for (pid, arm), rs in by.items():
        o = np.array([own_other(r, arm)[0] for r in rs])
        t = np.array([own_other(r, arm)[1] for r in rs])
        sel = o >= 0
        if not sel.any():
            skipped += 1
            continue
        liftA.append(t[sel].mean() - t.mean())
        runA.append(pid.split("_")[0])
    liftA, runA = np.array(liftA), np.array(runA)
    loA, hiA = cluster_boot(liftA, runA)

    # (B) selection by max own-batch child_sum instead of max margin (ties averaged)
    lift_cs, run_cs = selection_lift(by, lambda r, arm: own_other_child(r, arm)[0])
    lo_cs, hi_cs = cluster_boot(lift_cs, run_cs)

    print("\n== Task 1 robustness (no reference) ==")
    print(f"  selection lift (accept>=0 tie-tolerant; selected = accept set, {len(liftA)} cells, "
          f"{skipped} skipped no-accept): {liftA.mean():+.4f}  CI=[{loA:+.4f},{hiA:+.4f}]")
    print(f"  selection lift (select by max child_sum): {lift_cs.mean():+.4f}  CI=[{lo_cs:+.4f},{hi_cs:+.4f}]")


if __name__ == "__main__":
    main()
