"""Batch-swap v2 — Stage 0 ($0 ONLY). Pairing projection + overlap + cost + power + runtime.

MECHANICAL $0 GATE: monkeypatches gepa.lm.LM.__init__ to hard-fail at import, so ANY code path that would
instantiate an API client raises SystemExit. This script performs NO paid work. It ends by printing
"AWAITING APPROVED_V2" and stopping — the real failure-matched pairing (which needs B's parent run on
candidate B' examples) happens only in the PAID, APPROVED_V2-gated batch_swap_v2_run.py.

  HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/batch_swap_v2_stage0.py
"""
from __future__ import annotations

import csv
import json
import os

import numpy as np

# --- $0 tripwire: refuse to build any LM/API client -------------------------------------------------
import gepa.lm as _gepa_lm


def _no_lm(*_a, **_k):
    raise SystemExit("STAGE0 IS $0-ONLY: refusing to instantiate gepa.lm.LM (would enable a paid call)")


_gepa_lm.LM.__init__ = _no_lm  # any accidental LM(...) now hard-fails

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.scorer_inputs import trainset_meta, constraint_type

OUT = "analysis/ablation/batch_swap_v2"
K = 3            # recommended; Stage 0 reports both k=2 and k=3
SEED = 20260703
SIG2 = 0.0775   # single-draw margin variance (prior feedback-ablation run)
Z80 = 2.802     # z_{.975}+z_{.80} for two-sided 80%-power MDE
RATE_PROP, RATE_TASK = 0.011, 0.001


def main():
    os.makedirs(OUT, exist_ok=True)
    runs = [r for r in load_corpus() if r.b == 3]
    tm = trainset_meta()
    csets = tm["constraint_sets"]
    types_of = lambda tid: {constraint_type(c) for c in csets[tid]}

    # per-example corpus fail-propensity = mean 1[before_score<1] over all appearances (proxy for
    # "fails under an arbitrary parent"; the paid run uses B's ACTUAL parent).
    failp = {}
    acc = {}
    for r in runs:
        for c in r.cycles:
            for p, tid in enumerate(c.minibatch_ids):
                acc.setdefault(tid, []).append(1.0 if c.before_scores[p] < 1.0 else 0.0)
    failp = {t: float(np.mean(v)) for t, v in acc.items()}

    # batches + iteration terciles per run
    batches, terc = {}, {}
    for r in runs:
        its = sorted(c.iteration for c in r.cycles)
        q1, q2 = np.quantile(its, [1 / 3, 2 / 3])
        for c in r.cycles:
            batches[(r.seed, c.iteration)] = list(c.minibatch_ids)
            terc[(r.seed, c.iteration)] = 0 if c.iteration <= q1 else (1 if c.iteration <= q2 else 2)
    allb = sorted(batches)

    # candidate pairing with PROJECTED failure-match (>=2 of B''s 3 examples have failp>0.5),
    # deterministic least-used-first, most-likely-to-fail tiebreak.
    rng_order = sorted(allb, key=lambda B: (hash((SEED, B)) & 0xffffffff))
    drops, chosen, reuse, overlaps, rows = [], {}, {}, [], []
    for B in rng_order:
        s, _it = B
        bset = set(batches[B])
        bt = set().union(*[types_of(t) for t in batches[B]])
        cands = [X for X in allb if X != B and X[0] == s and terc[X] == terc[B] and not (set(batches[X]) & bset)]
        elig = [X for X in cands if sum(failp[t] > 0.5 for t in batches[X]) >= 2]
        if not elig:
            drops.append(B)
            continue
        elig.sort(key=lambda X: (reuse.get(X, 0), -sum(failp[t] for t in batches[X])))
        Bp = elig[0]
        chosen[B] = Bp
        reuse[Bp] = reuse.get(Bp, 0) + 1
        xt = set().union(*[types_of(t) for t in batches[Bp]])
        jac = len(bt & xt) / max(len(bt | xt), 1)
        overlaps.append(jac)
        rows.append({
            "B_id": f"s{B[0]}_it{B[1]}", "Bprime_id": f"s{Bp[0]}_it{Bp[1]}",
            "seed": B[0], "iteration": B[1], "tercile": terc[B],
            "Bprime_seed": Bp[0], "Bprime_iteration": Bp[1],
            "type_jaccard": round(jac, 4),
            "B_projfail": sum(failp[t] > 0.5 for t in batches[B]),
            "Bprime_projfail": sum(failp[t] > 0.5 for t in batches[Bp]),
            "B_ids": json.dumps(batches[B]), "Bprime_ids": json.dumps(batches[Bp]),
        })

    # emit projected pairing (the paid run RE-verifies failure-match on real parents and may reassign/drop)
    with open(f"{OUT}/pairing_projection.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    ov = np.array(overlaps)
    npair = len(chosen)
    ru = list(reuse.values())
    leverage = "HIGH-overlap risk (decomp weak)" if np.median(ov) > 0.7 else "usable spread"

    # ---- cost (per pair): 4 proposer + parent-on-B + parent-on-B' + 4 children x gate-on-{B,B'} + ~1 search
    prop = npair * 4
    task = npair * (2 * 3 + 4 * 2 * 3 + 3)   # parents(6) + child gates(24) + failure-match search(~3)
    cost = prop * RATE_PROP + task * RATE_TASK

    # ---- power: pooled specificity = within-B child difference (parent/batch/run structure cancels)
    def mde(k, rho):
        var_spec = 2 * (SIG2 / k)               # diff of two draw-avg child margins gated on same B
        deff = 1 + (npair / 8 - 1) * rho if rho > 0 else 1.0
        return Z80 * np.sqrt(var_spec / (npair / deff))

    # ---- runtime
    sec_per_pair = 75
    eta_h = npair * sec_per_pair / 3600

    lines = []
    P = lines.append
    P("# Batch-swap v2 — Stage 0 ($0) results\n")
    P(f"**Date:** 2026-07-02 · $0 read-only. Frozen corpus untouched. Writes under `{OUT}/`.\n")
    P("## 0.1 Pairing + PROJECTED failure-match")
    P(f"- per-example corpus fail-propensity: mean **{np.mean(list(failp.values())):.2f}**, "
      f"frac>0.5 = {np.mean([v > 0.5 for v in failp.values()]):.2f}")
    P(f"- eligible B (>=2 of B''s examples projected-fail): **{npair}/{len(allb)}**, drops **{len(drops)}**")
    P(f"- B' reuse min/mean/max = {min(ru)}/{np.mean(ru):.1f}/{max(ru)}")
    P("- NOTE: proxy only; the PAID run re-verifies ≥2 fails under B's ACTUAL parent, caches "
      "(parent,example) scores, and may reassign/drop (reported there).\n")
    P("## 0.2 Overlap leverage (constraint-type Jaccard B,B')")
    P(f"- mean {ov.mean():.2f}, median {np.median(ov):.2f}, p10 {np.percentile(ov,10):.2f}, "
      f"p90 {np.percentile(ov,90):.2f}, frac>0.8 {np.mean(ov>0.8):.2f} → **{leverage}**\n")
    P("## 0.3 Cost (rates $0.011/proposer, $0.001/task)")
    P(f"- pairs {npair} | proposer {prop} (${prop*RATE_PROP:.1f}) | task {task} (${task*RATE_TASK:.1f}) "
      f"| **total ~${cost:.0f}** (STOP $60, tripwire $55)\n")
    P("## 0.4 Power — pooled specificity MDE (k draw-avg, run-clustered; 8 clusters)")
    for k in (2, 3):
        for rho in (0.0, 0.05, 0.15):
            m = mde(k, rho)
            deff = 1 + (npair / 8 - 1) * rho if rho > 0 else 1.0
            P(f"- k={k} ρ={rho:.2f} DEFF={deff:.1f}: MDE={m:.3f} "
              f"[{'<=0.04 OK' if m <= 0.04 else 'MISS'}]")
    P("- specificity is a WITHIN-B child difference → run/batch structure cancels → ICC≈0 expected; "
      "adding draws does NOT fix clustering (only differencing does). Transfer (single margin) is wider.\n")
    P("## 0.5 Runtime")
    P(f"- ~{sec_per_pair}s/pair × {npair} → **ETA ~{eta_h:.1f}h** (<12h; caffeinate -dims, tee log).\n")
    P(f"Recommended **k={K}**. Pairing projection → `{OUT}/pairing_projection.csv`.\n")
    P("**AWAITING APPROVED_V2** — no paid work runs until Neel creates `analysis/ablation/APPROVED_V2`.")
    with open(f"{OUT}/plan.md", "w") as f:
        f.write("\n".join(lines) + "\n")

    print("\n".join(lines))
    print(f"\n[wrote {OUT}/pairing_projection.csv ({npair} rows) and {OUT}/plan.md]")


if __name__ == "__main__":
    main()
