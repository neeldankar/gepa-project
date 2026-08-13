"""§8a/§8b Stage-1 backfill: re-select each Stage-1 run's endpoint on the selection split, then
evaluate the 8 winners on the test split.

GATED: APPROVED-backfill (~$27.48). Also requires BOTH splits to exist (APPROVED-testsplit ->
build_test_split.py).

Produces the empirical endpoint distribution that §11-2's MDE simulation draws from. Under v2.1 the
endpoint is the **selection-split argmax**, so the backfill must use that estimator too: backfilling
the old val-argmax winners would draw the MDE's margins from a different estimator, whose spread is
inflated by exactly the tie-break lottery §8b removes (v2.1 §11-2).

    §8b endpoint, per seed:
        means[i] = mean over the 50 selection claims of candidate i's title recall
        best     = max(range(len(means)), key=lambda i: means[i])    # ties -> LOWEST index
        endpoint = test-split score of program_candidates[best]

    every candidate is scored, INCLUDING index 0 (the seed candidate)

COST. The 8 Stage-1 runs hold 97 candidates (11, 11, 13, 11, 14, 10, 13, 14) -- a realized count,
not an estimate:

    selection  97 x 50 x $0.004543  =  $22.03
    test        8 x 150 x $0.004543 =  $ 5.45
                                       -------
                                       $27.48

REPRICED 2026-08-11 (the numbers above are the M fit, kept because the gate was signed on them).
The completed §8b pass measured $0.005681/call across 15,150 calls -- 25% above the fit -- so the
realized cost of these same 6,050 calls is ~$34.37 ($37.03 at the conservative $0.006121 smoke
rate). SPEND_CAP moved 32.00 -> 44.00 accordingly; see the note there. M itself is deliberately NOT
re-fitted: it feeds the pre-spend estimate resolve() prints, where over-estimating is the silent
failure and under-estimating is the loud one -- the same call made in score_candidates.py:47.

RESUME. Per-seed selection results are checkpointed to backfill/seed{N}_selection.json and skipped
if present, so a crash costs at most one seed's selection pass (~$2.75), never the whole $22.

  --resolve   ($0)      identify the val-argmax candidates and print the pool sizes
  --run       (gated)   the full §8b re-selection + test evaluation
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
STAGE1 = os.path.join(REPO, "scratch", "hover_stage1")
SELECTION = os.path.join(HERE, "selection_split.json")
TEST = os.path.join(HERE, "test_split.json")
CKPT = os.path.join(HERE, "backfill")
OUT = os.path.join(HERE, "stage1_backfill_endpoints.json")

sys.path.insert(0, HERE)

M = 0.004543
# Hard tripwire. Raised 32.00 -> 44.00 on 2026-08-11: the $27.48 estimate below uses M, the stale
# $0.004543 fit. The completed §8b pass measured $0.005681/call over a 15,150-call sample, at which
# this job's 6,050 calls are $34.37 -- so the old cap would have raised during test eval ~6 of 8,
# about 7 h in, after all the selection work was done. $44.00 is 28% over that and 19% over the
# conservative $0.006121 smoke rate ($37.03); it is a runaway tripwire, not a budget, and still
# catches a >30% overrun. Margin is not tighter because B_seed7 came in 20% above its per-dir
# estimate, and the Stage-1 candidate prompts are not the same population as the state_dep ones.
# PER SEED (and per test eval), because the LM -- and therefore Meter's history window -- is now
# per seed. The largest seed is 14 candidates x 50 claims ~= $5.3; 8.00 mirrors the per-run-dir cap
# in score_candidates.py:48 and its margin.
SPEND_CAP = 8.00
JOB_CAP = 44.00    # the whole-job total, accumulated across those per-seed windows in `spent`
N_SEEDS = 8


def _result(seed: int) -> dict:
    return json.load(open(os.path.join(STAGE1, f"stage1_seed{seed}", "gepa_result.json")))


def val_argmax(seed: int) -> dict:
    """The OLD (v2 §8) endpoint convention, kept for the B10 comparison, not for the endpoint."""
    g = _result(seed)
    subs = g["prog_candidate_val_subscores"]
    agg = [sum(d.values()) / len(d) if d else float("-inf") for d in subs]
    best = max(range(len(agg)), key=lambda i: agg[i])  # ties -> lowest index (V5)
    return {
        "seed": seed,
        "n_candidates": len(subs),
        "val_best_idx": best,
        "val_best_agg": agg[best],
        "val_tied_indices": [i for i, v in enumerate(agg) if v == agg[best]],
        "val_tie_broken": sum(1 for v in agg if v == agg[best]) > 1,
        "val_returned_seed_prompt": best == 0,
    }


def resolve() -> int:
    print("=== Stage-1 candidate pools, and the OLD val-argmax convention (B10's table) ===")
    print(f"{'seed':>5} {'ncand':>6} {'val_best':>9} {'val_agg':>9} {'tied':>18}")
    rows = [val_argmax(s) for s in range(N_SEEDS)]
    for r in rows:
        print(f"{r['seed']:>5} {r['n_candidates']:>6} {r['val_best_idx']:>9} {r['val_best_agg']:>9.4f} "
              f"{str(r['val_tied_indices']):>18}"
              f"{'  <- TIE' if r['val_tie_broken'] else ''}"
              f"{'  <- SEED PROMPT' if r['val_returned_seed_prompt'] else ''}")
    n_cand = sum(r["n_candidates"] for r in rows)
    print(f"\n  candidates across the 8 runs : {n_cand}")
    print(f"  val tie-break fired          : {sum(r['val_tie_broken'] for r in rows)}/8 seeds")
    print(f"  val returned the seed prompt : {sum(r['val_returned_seed_prompt'] for r in rows)}/8 seeds")
    print("\n  Under v2.1 §8b these are NOT the endpoints. Every candidate is re-scored on the")
    print("  50-claim selection split and the argmax there is the endpoint.")
    print(f"  Cost: {n_cand} x 50 x ${M} = ${n_cand * 50 * M:.2f} selection "
          f"+ 8 x 150 x ${M} = ${8 * 150 * M:.2f} test  =>  ${(n_cand * 50 + 8 * 150) * M:.2f}")
    return 0


def run_live(workers: int | None = None) -> int:
    from gates import require

    gate = require("APPROVED-backfill")
    for p, why in ((SELECTION, "APPROVED-testsplit -> build_test_split.py"),
                   (TEST, "APPROVED-testsplit -> build_test_split.py")):
        if not os.path.exists(p):
            print(f"missing {p}: run {why} first")
            return 1

    import eval_split as ev

    sel = ev.load_split(SELECTION)
    test = ev.load_split(TEST)
    sel_sha, test_sha = ev.sha256_file(SELECTION), ev.sha256_file(TEST)
    os.makedirs(CKPT, exist_ok=True)

    dspy, probe = ev.bootstrap()
    base = ev.build_program(dspy, probe)
    workers = workers or ev.WORKERS

    # A FRESH LM PER SEED AND PER TEST EVAL, NOT ONE SHARED ACROSS THE JOB (score_candidates.py:88-93).
    # Meter.spend() sums the whole of lm.history (eval_split.py:121-127), and dspy bounds that history
    # at settings.max_history_size = 10000 entries. This job is 6050 metric calls x 6 LM calls =
    # 36,300 entries -- 3.6x the window. With one shared LM the window rolls at LM call 10,000, i.e.
    # candidate ~33 of 97, and from there spend() SILENTLY UNDERCOUNTS: the cap stops protecting
    # anything for two thirds of the run, and the spend_usd recorded below would be ~$10 against a
    # true ~$35. Per-seed keeps the largest window at 14 x 50 x 6 = 4200, and per-test-eval at 900.
    # `spent` accumulates the real total across those windows, and JOB_CAP guards it.
    spent = 0.0

    def job_guard() -> None:
        if spent > JOB_CAP:
            raise RuntimeError(f"JOB CAP: ${spent:.4f} > ${JOB_CAP:.2f} — aborting")

    print(f"[gate ok] {gate['gate']}  selection N={len(sel)}  test N={len(test)}  "
          f"cap ${SPEND_CAP}/seed, ${JOB_CAP} job, workers {workers}"
          f"{'' if workers == ev.WORKERS else f' (NOT the {ev.WORKERS} default)'}")

    rows = []
    for seed in range(N_SEEDS):
        g = _result(seed)
        cands = g["program_candidates"]
        ck = os.path.join(CKPT, f"seed{seed}_selection.json")
        if os.path.exists(ck):
            per_cand = json.load(open(ck))
            print(f"  seed {seed}: resumed {len(per_cand)} candidate scores from checkpoint ($0)")
        else:
            lm = ev.open_task_lm(dspy)              # fresh window per seed -- see the note above
            meter = ev.Meter(lm, probe, SPEND_CAP)
            per_cand = []
            for i, c in enumerate(cands):
                r = ev.score_candidate(dspy, probe, base, c, sel, lm, meter, workers)
                per_cand.append(r)
                print(f"  seed {seed} cand {i:>2}/{len(cands) - 1}  sel_mean={r['mean']:.4f}  "
                      f"${meter.spend():.3f} seed / ${spent + meter.spend():.3f} job  "
                      f"{r['elapsed_s']}s", flush=True)
            json.dump(per_cand, open(ck, "w"), indent=2)
            spent += meter.spend()
            job_guard()

        means = [r["mean"] for r in per_cand]
        best, ties = ev.argmax_lowest_index(means)
        row = val_argmax(seed)
        row.update({
            "sel_best_idx": best,
            "sel_best_mean": means[best],
            "sel_tied_indices": ties,
            "sel_tie_broken": len(ties) > 1,
            "sel_returned_seed_prompt": best == 0,
            "agrees_with_val_argmax": best == row["val_best_idx"],
            "selection_means": means,
        })
        rows.append(row)
        print(f"  seed {seed}: §8b winner = candidate {best} (sel_mean {means[best]:.4f}), "
              f"val-argmax was {row['val_best_idx']} -> "
              f"{'AGREE' if row['agrees_with_val_argmax'] else 'DIFFER'}", flush=True)

    print("\n=== test evaluation of the 8 §8b winners ===")
    for row in rows:
        seed = row["seed"]
        ck = os.path.join(CKPT, f"seed{seed}_test.json")
        if os.path.exists(ck):
            t = json.load(open(ck))
            print(f"  seed {seed}: resumed test score from checkpoint ($0)")
        else:
            lm = ev.open_task_lm(dspy)              # fresh window per test eval, same reason
            meter = ev.Meter(lm, probe, SPEND_CAP)
            cand = _result(seed)["program_candidates"][row["sel_best_idx"]]
            t = ev.score_candidate(dspy, probe, base, cand, test, lm, meter, workers)
            json.dump(t, open(ck, "w"), indent=2)
            spent += meter.spend()
            job_guard()
        row["endpoint_test_mean"] = t["mean"]
        row["endpoint_test_scores"] = t["scores"]
        print(f"  seed {seed}: endpoint test score = {t['mean']:.4f}", flush=True)

    endpoints = [r["endpoint_test_mean"] for r in rows]
    out = {
        "design": "state-dependent-design-v2.1-frozen §8b (selection-split argmax) -> §8a test split",
        "gate": gate,
        "selection_split": {"path": os.path.basename(SELECTION), "n": len(sel), "sha256": sel_sha},
        "test_split": {"path": os.path.basename(TEST), "n": len(test), "sha256": test_sha},
        "endpoints": endpoints,
        "n_selection_evals": sum(r["n_candidates"] for r in rows) * len(sel),
        "n_test_evals": N_SEEDS * len(test),
        "spend_usd": round(spent, 4),   # the accumulated job total, NOT one window's meter
        "b10_agreement": {
            "seeds_where_8b_differs_from_val_argmax": [r["seed"] for r in rows if not r["agrees_with_val_argmax"]],
            "val_tie_broken_seeds": [r["seed"] for r in rows if r["val_tie_broken"]],
            "val_seed_prompt_seeds": [r["seed"] for r in rows if r["val_returned_seed_prompt"]],
            "sel_seed_prompt_seeds": [r["seed"] for r in rows if r["sel_returned_seed_prompt"]],
            "sel_tie_broken_seeds": [r["seed"] for r in rows if r["sel_tie_broken"]],
        },
        "rows": rows,
    }
    json.dump(out, open(OUT, "w"), indent=2)

    n_diff = len(out["b10_agreement"]["seeds_where_8b_differs_from_val_argmax"])
    print(f"\n=== BACKFILL COMPLETE ===")
    print(f"  endpoints        : {[round(e, 4) for e in endpoints]}")
    print(f"  mean / sd        : {sum(endpoints) / len(endpoints):.4f} / "
          f"{(sum((e - sum(endpoints) / len(endpoints)) ** 2 for e in endpoints) / len(endpoints)) ** 0.5:.4f}")
    print(f"  §8b differs from val-argmax on {n_diff}/8 seeds  (the direct measure of B10's cost)")
    print(f"  spend            : ${spent:.4f} (job cap ${JOB_CAP}; ${SPEND_CAP}/seed)"
          f"{'   [resumed seeds cost $0 and are not in this figure]' if spent == 0 else ''}")
    print(f"  wrote            : {os.path.basename(OUT)}")
    print(f"  next             : mde_sim.py --endpoints {os.path.basename(OUT)} --dose D")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--resolve", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--workers", type=int, default=None,
                    help="per-candidate evaluation threads (default eval_split.WORKERS = 8). This "
                         "script is ONE process with serial seed/candidate/test loops, so workers "
                         "is its only concurrency knob -- unlike supervisor.py --score, which buys "
                         "concurrency with processes at SCORE_WIDTH.")
    a = ap.parse_args()
    if a.resolve:
        raise SystemExit(resolve())
    if a.run:
        raise SystemExit(run_live(a.workers))
    ap.error("pick --resolve ($0) or --run (gated)")
