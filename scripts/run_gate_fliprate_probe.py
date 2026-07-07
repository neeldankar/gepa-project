"""Gate flip-rate probe ($0, read-only, IFBench frozen corpus).

For each LOGGED-REJECTED b3 child, does it FLIP to accept under an AGGREGATE rule (vs the pointwise
"child beats parent on the minibatch" gate)? Rules implemented from the brief (no committed gate-pivot
doc exists), each specifiable from logged per-constraint binary scores:

  R1 majority-fix        : child satisfies a MAJORITY of the constraints the parent failed
                           flip iff |{parent-failed that child now passes}| / |parent-failed| > 0.5
  R2 minimax-lineage     : worst-case — flip iff the child STRICTLY IMPROVES the constraint TYPE that
                           the lineage persistently fails most (history window = all prior cycles in the
                           run; fallback to corpus type fail-rate if unseen)
  R3 weighted-coverage   : boosting — weight each constraint by corpus difficulty (global type
                           fail-rate); flip iff weighted child score > weighted parent score

HONESTY GUARD: the corpus CANNOT say a flip would improve U (rejected children never got a valset eval
— acceptance gates the broad eval; that's the collider). This answers ONLY "does the aggregate gate
behave differently from pointwise at all." Never read flip-rate as evidence the gate works.

Run: HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/run_gate_fliprate_probe.py
"""
from __future__ import annotations

import collections

import numpy as np

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.scorer_inputs import constraint_type, type_failrate

GFR = type_failrate()          # {type: corpus fail-rate}
GLOBAL_FR = float(np.mean(list(GFR.values())))


def instances(cycle):
    """Flatten (parent, child, type) per constraint-instance over the b examples."""
    out = []
    for pd, cd in zip(cycle.parent_objscores, cycle.child_objscores):
        for cid, pv in pd.items():
            cv = cd.get(cid)
            if cv is None:
                continue
            out.append((float(pv), float(cv), constraint_type(cid)))
    return out


def lineage_failrate(prior_cycles):
    """{type: parent fail-rate} over all prior cycles in the run (expanding window)."""
    fails = collections.Counter(); tot = collections.Counter()
    for c in prior_cycles:
        for pd in c.parent_objscores:
            for cid, pv in pd.items():
                t = constraint_type(cid); tot[t] += 1; fails[t] += (1 if pv == 0.0 else 0)
    return {t: fails[t] / tot[t] for t in tot}


def r1_majority_fix(inst):
    failed = [(p, c) for p, c, _ in inst if p == 0.0]
    if not failed:
        return False
    fixed = sum(1 for p, c in failed if c == 1.0)
    return (fixed / len(failed)) > 0.5


def r2_minimax_lineage(inst, lin_fr):
    if not inst:
        return False
    def w(t):
        return lin_fr.get(t, GFR.get(t, GLOBAL_FR))
    worst = max((t for _, _, t in inst), key=w)                 # persistently-failed type present
    pc = sum(p for p, _, t in inst if t == worst)
    cc = sum(c for _, c, t in inst if t == worst)
    return cc > pc                                              # child strictly improves the worst bucket


def r3_weighted_coverage(inst):
    wp = sum(GFR.get(t, GLOBAL_FR) * p for p, _, t in inst)
    wc = sum(GFR.get(t, GLOBAL_FR) * c for _, c, t in inst)
    return wc > wp


def trade(inst):
    fixes = [(t) for p, c, t in inst if p == 0.0 and c == 1.0]
    losses = [(t) for p, c, t in inst if p == 1.0 and c == 0.0]
    return fixes, losses


def main():
    runs = [r for r in load_corpus() if r.b == 3]
    rejected = []
    for run in runs:
        prior = []
        for c in sorted(run.cycles, key=lambda x: x.iteration):
            if (not c.accept) and c.child_objscores is not None:
                inst = instances(c)
                rejected.append((run.seed, c.iteration, inst, lineage_failrate(prior), c))
            prior.append(c)
    N = len(rejected)
    print(f"logged-rejected b3 children with per-constraint scores: N={N}\n")

    flips = {"R1_majority_fix": [], "R2_minimax_lineage": [], "R3_weighted_coverage": []}
    for seed, it, inst, lin, cyc in rejected:
        if r1_majority_fix(inst):
            flips["R1_majority_fix"].append((seed, it))
        if r2_minimax_lineage(inst, lin):
            flips["R2_minimax_lineage"].append((seed, it))
        if r3_weighted_coverage(inst):
            flips["R3_weighted_coverage"].append((seed, it))

    print("=" * 78)
    print("FLIP-RATE TABLE (rule | flips/N | rate | median (fixed,lost) | fixed-diff vs lost-diff)")
    print("=" * 78)
    flipset = {k: set(v) for k, v in flips.items()}
    rej_by_key = {(s, it): (inst, cyc) for s, it, inst, _, cyc in rejected}
    for rule, fl in flips.items():
        rate = len(fl) / N
        # trade distribution over flipped children
        fx, ls, fxd, lsd = [], [], [], []
        for key in fl:
            inst, _ = rej_by_key[key]
            fixes, losses = trade(inst)
            fx.append(len(fixes)); ls.append(len(losses))
            fxd += [GFR.get(t, GLOBAL_FR) for t in fixes]
            lsd += [GFR.get(t, GLOBAL_FR) for t in losses]
        med = (int(np.median(fx)) if fx else 0, int(np.median(ls)) if ls else 0)
        print(f"  {rule:22} {len(fl):3}/{N}  rate={rate:5.1%}  median(fix,lost)={med}  "
              f"fixed-difficulty={np.mean(fxd) if fxd else float('nan'):.2f} vs lost-difficulty={np.mean(lsd) if lsd else float('nan'):.2f}")

    # trade distribution detail (joint histogram of (fixes,losses)) per rule
    print("\n--- trade distribution: (#fixed,#lost) -> count of flips ---")
    for rule, fl in flips.items():
        hist = collections.Counter()
        for key in fl:
            inst, _ = rej_by_key[key]
            fixes, losses = trade(inst)
            hist[(len(fixes), len(losses))] += 1
        top = sorted(hist.items(), key=lambda kv: -kv[1])[:8]
        print(f"  {rule:22} {dict(top)}")
        # target texture: fixes>=2 stubborn AND loses<=1 easy (fixed-diff>lost-diff)
        tgt = 0
        for key in fl:
            inst, _ = rej_by_key[key]
            fixes, losses = trade(inst)
            fd = np.mean([GFR.get(t, GLOBAL_FR) for t in fixes]) if fixes else 0
            ld = np.mean([GFR.get(t, GLOBAL_FR) for t in losses]) if losses else 0
            if len(fixes) >= 2 and len(losses) <= 1 and fd >= ld:
                tgt += 1
        print(f"      -> 'fix>=2 stubborn, lose<=1 easier' flips: {tgt}/{len(fl)}")

    # overlap
    print("\n--- overlap between rules (do they flip the same children?) ---")
    keys = list(flipset)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = flipset[keys[i]], flipset[keys[j]]
            inter = len(a & b); uni = len(a | b)
            print(f"  {keys[i]} ∩ {keys[j]}: {inter}  (Jaccard={inter/uni if uni else 0:.2f})")
    allthree = flipset["R1_majority_fix"] & flipset["R2_minimax_lineage"] & flipset["R3_weighted_coverage"]
    anyrule = flipset["R1_majority_fix"] | flipset["R2_minimax_lineage"] | flipset["R3_weighted_coverage"]
    print(f"  flipped by ALL 3: {len(allthree)}  | flipped by ANY rule: {len(anyrule)}/{N} ({len(anyrule)/N:.1%})")

    # verbatim flipped events (pick ones showing texture: prefer multi-fix, low-loss)
    print("\n" + "=" * 78 + "\nVERBATIM FLIPPED EVENTS\n" + "=" * 78)
    shown = 0
    ranked = sorted(anyrule, key=lambda key: -len(trade(rej_by_key[key][0])[0]))  # most fixes first
    for key in ranked:
        inst, cyc = rej_by_key[key]
        fixes, losses = trade(inst)
        which = [r for r in flips if key in flipset[r]]
        if shown >= 4:
            break
        shown += 1
        print(f"\n[seed{key[0]} it{key[1]}]  flips under: {which}")
        print(f"  fixes={len(fixes)} (types {collections.Counter(fixes)})  losses={len(losses)} (types {collections.Counter(losses)})")
        for ex_i, (pd, cd) in enumerate(zip(cyc.parent_objscores, cyc.child_objscores)):
            for cid in pd:
                pv, cv = pd[cid], cd.get(cid)
                mark = "FIX " if (pv == 0 and cv == 1) else ("LOSS" if (pv == 1 and cv == 0) else "    ")
                if mark.strip():
                    print(f"    ex{ex_i} {mark} {cid:42} parent={pv} child={cv} (type-difficulty={GFR.get(constraint_type(cid),GLOBAL_FR):.2f})")

    print("\nDONE — $0 read-only, IFBench only (HoVer has no per-doc parent/child binary).")


if __name__ == "__main__":
    main()
