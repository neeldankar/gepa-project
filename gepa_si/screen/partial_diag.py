"""Partial-cell diagnosis (Step 4): unsampled (benign) vs tradeoff (adversarial).

The only live target is partial->full conversion. WHY don't partial cells finish?
 - BENIGN: the fix exists, the right reflection input just wasn't drawn (curriculum lever alive).
 - ADVERSARIAL: satisfying one constraint breaks another on the same example (no per-example
   selection scorer fixes it; representational, not curricular).

LIMITATION: per-constraint satisfaction is logged only at the MINIBATCH (trainset) level — the
valset stores scalar fractions only. So this characterizes reflection's behavior on its INPUT
examples (same dataset distribution as valset), NOT the 150 valset cells from Step 3.

Per iteration, the BEFORE eval (parent) and AFTER eval (proposed child) carry per-constraint
objective_scores on the SAME minibatch examples — enabling a direct parent->child tradeoff test.
"""

from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np

from gepa_si.screen.corpus_io import RunData


def constraint_type(cid: str) -> str:
    """Category bucket = prefix before ':' (after stripping the '#index' dedup suffix)."""
    return cid.split("#", 1)[0].split(":", 1)[0]


def base_id(cid: str) -> str:
    return cid.split("#", 1)[0]


# ---------- Part A1: which constraint stays unsatisfied on partial cells ----------
def unsatisfied_on_partial(runs: list[RunData]) -> dict:
    """Over all PARTIAL parent minibatch cells (>1 constraint, 0<frac<1): unsatisfied-by-type
    counts, plus per-type failure RATE = unsatisfied / appearances (base-rate controlled)."""
    unsat_type = Counter()          # unsatisfied constraints on partial cells, by type
    appear_type = Counter()         # all constraint appearances on partial cells, by type
    appear_all_type = Counter()     # appearances across ALL cells (context)
    fail_all_type = Counter()       # unsatisfied across ALL cells
    n_partial = 0
    n_cells = 0
    for run in runs:
        for c in run.cycles:
            for ex in c.parent_objscores:
                if not ex:
                    continue
                n_cells += 1
                vals = list(ex.values())
                n_ok = sum(1 for v in vals if v == 1.0)
                n = len(vals)
                # all-cell context
                for cid, v in ex.items():
                    t = constraint_type(cid)
                    appear_all_type[t] += 1
                    if v == 0.0:
                        fail_all_type[t] += 1
                # partial = multi-constraint, some-but-not-all satisfied
                if n > 1 and 0 < n_ok < n:
                    n_partial += 1
                    for cid, v in ex.items():
                        t = constraint_type(cid)
                        appear_type[t] += 1
                        if v == 0.0:
                            unsat_type[t] += 1
    rows = []
    for t in sorted(appear_type, key=lambda x: -unsat_type[x]):
        rows.append({
            "type": t,
            "unsat_on_partial": unsat_type[t],
            "appears_on_partial": appear_type[t],
            "fail_rate_partial": unsat_type[t] / appear_type[t] if appear_type[t] else 0.0,
            "fail_rate_overall": fail_all_type[t] / appear_all_type[t] if appear_all_type[t] else 0.0,
        })
    total_unsat = sum(unsat_type.values())
    top3 = sum(sorted(unsat_type.values(), reverse=True)[:3])
    return {
        "n_cells": n_cells, "n_partial_cells": n_partial,
        "n_types_seen": len(appear_type), "total_unsat": total_unsat,
        "top3_share": top3 / total_unsat if total_unsat else 0.0,
        "rows": rows,
    }


# ---------- Part A2: flip consistency on trainset examples (proxy for Step-3 swingable) ----------
def flip_consistency(runs: list[RunData]) -> dict:
    """For each (trainset example id, base constraint id) seen >=2x across the corpus with both a
    pass and a fail, the constraint is 'flipping'. Are flips concentrated in a few TYPES?"""
    # (train_id, base_cid) -> list of 0/1 outcomes (parent evals only)
    obs: dict[tuple[int, str], list[int]] = defaultdict(list)
    for run in runs:
        for c in run.cycles:
            for mb_id, ex in zip(c.minibatch_ids, c.parent_objscores):
                for cid, v in (ex or {}).items():
                    obs[(mb_id, base_id(cid))].append(int(v == 1.0))
    flip_type = Counter()
    stable_type = Counter()
    n_flip = n_stable = 0
    for (mb_id, bcid), outs in obs.items():
        if len(outs) < 2:
            continue
        t = constraint_type(bcid)
        if 0 in outs and 1 in outs:
            flip_type[t] += 1
            n_flip += 1
        else:
            stable_type[t] += 1
            n_stable += 1
    rows = []
    for t in sorted(flip_type, key=lambda x: -flip_type[x]):
        tot = flip_type[t] + stable_type[t]
        rows.append({"type": t, "flips": flip_type[t], "stable": stable_type[t],
                     "flip_rate": flip_type[t] / tot if tot else 0.0})
    top3 = sum(sorted(flip_type.values(), reverse=True)[:3])
    return {"n_pairs_multiseen": n_flip + n_stable, "n_flipping": n_flip,
            "top3_flip_share": top3 / n_flip if n_flip else 0.0, "rows": rows}


# ---------- Part B3: tradeoff test (parent -> child per-constraint on same minibatch cell) ----------
def tradeoff_stats(runs: list[RunData], accepted_only: bool) -> dict:
    n_improve = n_regress = 0
    n_cells = 0
    n_cells_with_improve = 0
    n_coregress = 0                 # cells with >=1 improve AND >=1 regress (the smoking gun)
    pair_counter = Counter()        # (improved_type, regressed_type) co-occurrence within a cell
    deltas = []                     # child_satcount - parent_satcount, per cell
    for run in runs:
        for c in run.cycles:
            if c.child_objscores is None:
                continue
            if accepted_only and not c.accept:
                continue
            for pex, cex in zip(c.parent_objscores, c.child_objscores):
                keys = set(pex) & set(cex)   # constraints present in both
                if not keys:
                    continue
                n_cells += 1
                improved = [k for k in keys if pex[k] == 0.0 and cex[k] == 1.0]
                regressed = [k for k in keys if pex[k] == 1.0 and cex[k] == 0.0]
                n_improve += len(improved)
                n_regress += len(regressed)
                deltas.append(sum(cex[k] == 1.0 for k in keys) - sum(pex[k] == 1.0 for k in keys))
                if improved:
                    n_cells_with_improve += 1
                if improved and regressed:
                    n_coregress += 1
                    for iu in improved:
                        for rd in regressed:
                            pair_counter[(constraint_type(iu), constraint_type(rd))] += 1
    deltas = np.array(deltas) if deltas else np.array([0])
    return {
        "scope": "accepted" if accepted_only else "all_proposals",
        "n_cells": n_cells, "n_improve": n_improve, "n_regress": n_regress,
        "n_cells_with_improve": n_cells_with_improve,
        "n_coregress": n_coregress,
        # of cells that improved >=1 constraint, what fraction ALSO regressed >=1 (the smoking gun)
        "coregress_frac_of_improving": n_coregress / n_cells_with_improve if n_cells_with_improve else 0.0,
        "coregress_frac_of_all": n_coregress / n_cells if n_cells else 0.0,
        "regress_per_improve": n_regress / n_improve if n_improve else float("inf"),
        "delta_mean": float(deltas.mean()), "delta_median": float(np.median(deltas)),
        "delta_frac_neg": float(np.mean(deltas < 0)), "delta_frac_pos": float(np.mean(deltas > 0)),
        "top_pairs": pair_counter.most_common(8),
    }


# ---------- Part B4: within-example trajectory (sparse) ----------
def trajectory(runs: list[RunData]) -> dict:
    """For trainset examples sampled >=2x in a run, the parent satisfied-FRACTION sequence (ordered
    by iteration): does it climb (benign — fixes accumulate) or plateau/oscillate below full
    (adversarial — never simultaneously held)? Restricted to series that are NOT already full at
    every appearance (an always-full example has no room to move and would inflate 'plateau')."""
    reached_full = climbed_not_full = flat_stuck = oscillate = 0
    n_series = n_already_full = 0
    for run in runs:
        seq: dict[int, list[tuple[int, int, int]]] = defaultdict(list)  # train_id -> [(iter, n_ok, n)]
        for c in run.cycles:
            for mb_id, ex in zip(c.minibatch_ids, c.parent_objscores):
                if ex:
                    seq[mb_id].append((c.iteration, sum(v == 1.0 for v in ex.values()), len(ex)))
        for mb_id, pts in seq.items():
            if len(pts) < 2:
                continue
            pts.sort()
            frac = np.array([p[1] / p[2] for p in pts])  # satisfied fraction, normalises mixed n
            if np.all(frac >= 1.0):
                n_already_full += 1          # no room to climb; excluded from the stuck analysis
                continue
            n_series += 1
            diffs = np.diff(frac)
            if frac[-1] >= 1.0:
                reached_full += 1            # eventually solved -> benign
            elif np.all(diffs >= 0) and np.any(diffs > 0):
                climbed_not_full += 1        # improving but not yet full
            elif np.all(diffs == 0):
                flat_stuck += 1              # never moves -> adversarial / hard
            else:
                oscillate += 1
    return {"n_series": n_series, "n_already_full": n_already_full,
            "reached_full": reached_full, "climbed_not_full": climbed_not_full,
            "flat_stuck": flat_stuck, "oscillate": oscillate}
