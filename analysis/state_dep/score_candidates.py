"""§8b post-run pass: score a completed run's candidates on the selection split, take the argmax,
evaluate that candidate on the test split. GATED: APPROVED-liverun.

This is the endpoint. Nothing mid-flight touches either split; this runs after the budget counter
has exhausted and is outside it (v2.1 §8a, §8b).

    means[i] = mean over the 50 selection claims of candidate i's title recall,
               for EVERY candidate including index 0 (the seed candidate)
    best     = max(range(len(means)), key=lambda i: means[i])       # ties -> LOWEST index
    endpoint = test-split score of program_candidates[best]

    midpoint endpoint (v2.1 §8, R13-c; only when a §9 ambiguity rule demands it):
        the same argmax restricted to candidates with
        num_metric_calls_by_discovery <= max_metric_calls / 2.

        WHICH CANDIDATE the midpoint rule picks is identified and recorded on EVERY run, always,
        because the selection scores it needs are already computed here and it therefore costs
        nothing. Its TEST EVALUATION is not budgeted (Neel, 2026-07-23: dropped, -$16 across 24
        runs) and happens only under --midpoint. That is exactly the conditional §8/§9 already
        describe -- "evaluated only if a map cell's ambiguity rule demands it" -- so the option
        stays open on the specific runs a §9 cell calls for, at $0.68 each, rather than being
        prepaid on all 24.

COST per run: n_candidates x 50 selection calls (~$2.3-3.2), plus 150 test calls (~$0.68).
--midpoint adds 150 more (~$0.68) on the runs it is passed for.

RESUME: selection scores are checkpointed per run dir; re-running skips what exists.

  --run DIR      one run directory under runs/
  --all          every run dir holding a run_summary.json
  --midpoint     additionally evaluate the midpoint-restricted argmax on test
  --dry-run      $0: print what would be evaluated and what it would cost
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
SELECTION = os.path.join(HERE, "selection_split.json")
TEST = os.path.join(HERE, "test_split.json")
sys.path.insert(0, HERE)

M = 0.004543
SPEND_CAP = 6.00  # per run dir; a run's post-pass is ~$3-4.5
MAX_METRIC_CALLS = 300  # must match run_state_dep.MAX_METRIC_CALLS; asserted against config.json


def gates_for(dirs: list[str]) -> list[str]:
    """Which APPROVED file each run dir's post-run pass belongs to.

    The smoke's own selection and test evaluations are part of the smoke's cost and therefore sit
    behind APPROVED-smoke, not APPROVED-liverun (v2.1.1 §13-7). A mixed --all invocation needs BOTH,
    and requires both -- it never proceeds on the strength of whichever it happens to find.
    """
    need = set()
    for d in dirs:
        cfg = os.path.join(d, "config.json")
        smoke = json.load(open(cfg)).get("smoke", False) if os.path.exists(cfg) else False
        need.add("APPROVED-smoke" if smoke else "APPROVED-liverun")
    return sorted(need)


def run_dirs(one: str | None) -> list[str]:
    if one:
        return [one if os.path.isabs(one) else os.path.join(RUNS, one)]
    if not os.path.isdir(RUNS):
        return []
    return sorted(
        os.path.join(RUNS, d) for d in os.listdir(RUNS)
        if os.path.exists(os.path.join(RUNS, d, "run_summary.json"))
    )


def process(d: str, ev, dspy, probe, base, lm, sel, test, want_midpoint: bool) -> dict:
    g = json.load(open(os.path.join(d, "gepa_result.json")))
    cands = g["program_candidates"]
    discovery = g["num_metric_calls_by_discovery"]
    cfg = json.load(open(os.path.join(d, "config.json")))
    assert cfg["max_metric_calls"] == MAX_METRIC_CALLS, (
        f"{d}: run used max_metric_calls={cfg['max_metric_calls']}, midpoint rule assumes "
        f"{MAX_METRIC_CALLS}")

    meter = ev.Meter(lm, probe, SPEND_CAP)
    ck = os.path.join(d, "selection_scores.json")
    if os.path.exists(ck):
        per_cand = json.load(open(ck))
        print(f"  {os.path.basename(d)}: resumed {len(per_cand)} selection scores ($0)")
    else:
        per_cand = []
        for i, c in enumerate(cands):
            r = ev.score_candidate(dspy, probe, base, c, sel, lm, meter)
            per_cand.append(r)
            print(f"    cand {i:>2}/{len(cands) - 1}  sel_mean={r['mean']:.4f}  "
                  f"${meter.spend():.3f}  {r['elapsed_s']}s", flush=True)
        json.dump(per_cand, open(ck, "w"), indent=2)

    means = [r["mean"] for r in per_cand]
    best, ties = ev.argmax_lowest_index(means)

    # the val-argmax the run WOULD have returned under v2 §8, for the B10 agreement descriptive
    subs = g["prog_candidate_val_subscores"]
    vagg = [sum(x.values()) / len(x) if x else float("-inf") for x in subs]
    vbest, vties = ev.argmax_lowest_index(vagg)

    endpoint = ev.score_candidate(dspy, probe, base, cands[best], test, lm, meter)
    out = {
        "run": os.path.basename(d),
        "arm": cfg["arm"], "seed": cfg["seed"], "smoke": cfg.get("smoke", False),
        "n_candidates": len(cands),
        "selection_split": {"n": len(sel), "sha256": ev.sha256_file(SELECTION)},
        "test_split": {"n": len(test), "sha256": ev.sha256_file(TEST)},
        "selection_means": means,
        "sel_best_idx": best, "sel_tied_indices": ties, "sel_tie_broken": len(ties) > 1,
        "sel_returned_seed_prompt": best == 0,
        "val_best_idx": vbest, "val_tied_indices": vties, "val_tie_broken": len(vties) > 1,
        "agrees_with_val_argmax": best == vbest,
        "endpoint_test_mean": endpoint["mean"],
        "endpoint_test_scores": endpoint["scores"],
        "post_run_spend_usd": None,
    }

    # Identifying the midpoint candidate is free — always done. Evaluating it on test is not.
    cutoff = MAX_METRIC_CALLS / 2
    eligible = [i for i, n in enumerate(discovery) if n <= cutoff]
    assert eligible, f"{d}: no candidate discovered by the midpoint — impossible, the seed is 0"
    local, _ = ev.argmax_lowest_index([means[i] for i in eligible])
    mid_idx = eligible[local]
    out["midpoint"] = {
        "budget_cutoff": cutoff,
        "eligible_candidates": eligible,
        "best_idx": mid_idx,
        "same_as_primary": mid_idx == best,
        "test_mean": None,      # unbudgeted (Neel 2026-07-23); fill by re-running with --midpoint
        "test_scores": None,
        "test_evaluated": False,
    }
    if want_midpoint:
        mid = ev.score_candidate(dspy, probe, base, cands[mid_idx], test, lm, meter)
        out["midpoint"].update(test_mean=mid["mean"], test_scores=mid["scores"],
                               test_evaluated=True)

    out["post_run_spend_usd"] = round(meter.spend(), 4)
    json.dump(out, open(os.path.join(d, "endpoints.json"), "w"), indent=2)
    print(f"  {out['run']}: §8b winner = cand {best} (sel {means[best]:.4f}) -> "
          f"TEST {endpoint['mean']:.4f}   [val-argmax was {vbest}: "
          f"{'AGREE' if out['agrees_with_val_argmax'] else 'DIFFER'}]   ${out['post_run_spend_usd']:.3f}",
          flush=True)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--midpoint", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not (a.run or a.all):
        ap.error("pick --run DIR or --all")

    dirs = run_dirs(a.run)
    total_cands = 0
    for d in dirs:
        g = os.path.join(d, "gepa_result.json")
        total_cands += len(json.load(open(g))["program_candidates"]) if os.path.exists(g) else 0
    n_test = 2 if a.midpoint else 1
    est = (total_cands * 50 + len(dirs) * n_test * 150) * M

    print(f"=== §8b post-run selection pass ===")
    print(f"  run dirs        : {len(dirs)}")
    print(f"  gates required  : {', '.join(gates_for(dirs)) or 'APPROVED-liverun'}")
    print(f"  candidates      : {total_cands}")
    print(f"  selection evals : {total_cands} x 50 = {total_cands * 50}")
    print(f"  test evals      : {len(dirs)} x {n_test} x 150 = {len(dirs) * n_test * 150}"
          f"{'  (primary + midpoint)' if a.midpoint else '  (primary only; midpoint unbudgeted)'}")
    print(f"  estimated spend : ~${est:.2f}")

    if a.dry_run:
        print("\n[dry-run] no gate check, no evaluation, no spend.")
        return 0

    # The gate is checked before anything else on the live path, even when there is nothing to do:
    # "no APPROVED, no launch" is a property of the script, not of whether the work happens to be
    # empty today. With no run dirs at all we still demand APPROVED-liverun, the broader gate.
    from gates import require
    for g in (gates_for(dirs) or ["APPROVED-liverun"]):
        require(g)
    if not dirs:
        print("no completed run directories found")
        return 1
    for p in (SELECTION, TEST):
        if not os.path.exists(p):
            print(f"missing {p}: build_test_split.py must run first (APPROVED-testsplit)")
            return 1

    import eval_split as ev
    sel, test = ev.load_split(SELECTION), ev.load_split(TEST)
    dspy, probe = ev.bootstrap()
    lm = ev.open_task_lm(dspy)
    base = ev.build_program(dspy, probe)

    rows = [process(d, ev, dspy, probe, base, lm, sel, test, a.midpoint) for d in dirs]

    n_diff = sum(1 for r in rows if not r["agrees_with_val_argmax"])
    n_seed = sum(1 for r in rows if r["sel_returned_seed_prompt"])
    print(f"\n=== POST-RUN PASS COMPLETE ===")
    print(f"  runs scored                       : {len(rows)}")
    print(f"  §8b differs from val-argmax       : {n_diff}/{len(rows)}  (B10's realized cost)")
    print(f"  endpoint is the seed prompt       : {n_seed}/{len(rows)}")
    print(f"  spend                             : ${sum(r['post_run_spend_usd'] for r in rows):.4f}")
    print(f"  per-run endpoints are in <run>/endpoints.json — results.md is NOT written here")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
