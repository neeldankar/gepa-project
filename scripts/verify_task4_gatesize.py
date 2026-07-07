"""Task 4 — gate-size probe ($0, reads b3 + b1 JSONL logs; no API calls).

Scope (per approved plan / user decision):
  4A  decision instability of the ORIGINAL b3 gate for the 382 batch-swap batches.
      Per-example parent (before.scores) and ORIGINAL child (after.scores) come from the b3 logs.
      Accept rule = Task 2 rule: strict sum(child) > sum(parent) over the gated examples.
      Subsample b=3 -> b'=1 (3 single-example subsets) and b'=2 (3 pairs); report
      P(subsampled decision != full b=3), overall + per run, and within-b' disagreement.
      Validate recomputed b=3 accept vs the LOGGED accept.
  4C  b=1 baselines: accept rate + same-input (example-id) repeat disagreement across cycles.
  4B  INFEASIBLE offline (batch-swap child-draw per-example scores were never persisted) -> reported,
      not computed here.

    HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/verify_task4_gatesize.py
"""
from __future__ import annotations

import csv
import glob
import json
from itertools import combinations

import numpy as np

OUT = "analysis/ablation/batch_swap_v2"


def parse_cycles(log_path):
    """(seed,iteration) -> dict(before_scores, after_scores, mb_ids, logged_accept)."""
    recs = [json.loads(l) for l in open(log_path) if l.strip()]
    by_it = {}
    for r in recs:
        it = r.get("iteration")
        if it is None or r.get("event") in ("meta", "optimization_start", "optimization_end"):
            continue
        by_it.setdefault(it, []).append(r)
    out = {}
    for it, evs in by_it.items():
        kinds = {e["event"] for e in evs}
        if "minibatch_sampled" not in kinds or "reflective_dataset_built" not in kinds:
            continue
        mb = next(e for e in evs if e["event"] == "minibatch_sampled")
        evals = [e for e in evs if e["event"] == "evaluation_end"]
        before = next((e for e in evals if e.get("candidate_idx") is not None), None)
        after = next((e for e in evals if e.get("candidate_idx") is None), None)
        if before is None or after is None:
            continue
        acc_ev = next((e for e in evs if e["event"] == "candidate_accepted"), None)
        rej_ev = next((e for e in evs if e["event"] == "candidate_rejected"), None)
        logged = acc_ev is not None if (acc_ev is None) != (rej_ev is None) else None
        out[it] = dict(
            before=list(before.get("scores") or []),
            after=list(after.get("scores") or []),
            mb_ids=list(mb.get("minibatch_ids") or []),
            logged=logged,
        )
    return out


def load_logs(b):
    """seed -> {iteration: cycle} for completed mm=2500 runs of given b."""
    runs = {}
    for cfgp in glob.glob("logs/*.config.json"):
        try:
            cfg = json.load(open(cfgp))
        except Exception:
            continue
        if cfg.get("max_metric_calls") == 2500 and cfg.get("results", {}).get("completed") \
                and cfg.get("b") == b:
            runs[cfg["seed"]] = parse_cycles(cfg["log_path"])
    return runs


def accept(child_subset, parent_subset):
    """Task 2 / native-gate rule: strict sum(child) > sum(parent) over the subset.
    Computed exactly as GEPA does (StrictImprovementAcceptance: new_sum > old_sum) to
    reproduce tie handling (equal sums -> reject); avoids summing elementwise diffs,
    which would introduce float residuals at ties."""
    return float(np.sum(child_subset)) > float(np.sum(parent_subset))


def main():
    b3 = load_logs(3)
    pairs = list(csv.DictReader(open(f"{OUT}/pairing.csv")))

    # ---- 4A: original-gate decision instability on the 382 batches ----
    rows = []  # (seed, full_accept, logged, b1_diffs[list of 3 bools], b2_diffs[list of 3 bools],
    #             within1_disagree, within2_disagree)
    miss = 0
    valid_val = 0
    val_match = 0
    for row in pairs:
        seed, it = int(row["seed"]), int(row["iteration"])
        cyc = b3.get(seed, {}).get(it)
        if cyc is None or len(cyc["before"]) != 3 or len(cyc["after"]) != 3:
            miss += 1
            continue
        ch, pa = np.array(cyc["after"]), np.array(cyc["before"])  # child, parent per-example
        full = accept(ch, pa)
        # validate vs logged accept
        if cyc["logged"] is not None:
            valid_val += 1
            val_match += int(cyc["logged"] == full)
        # b'=1: 3 single-example gates
        d1 = [accept([ch[i]], [pa[i]]) for i in range(3)]
        # b'=2: 3 pairs
        d2 = [accept([ch[i], ch[j]], [pa[i], pa[j]]) for i, j in combinations(range(3), 2)]
        rows.append(dict(
            seed=seed, full=full,
            b1_diff=[int(x != full) for x in d1],
            b2_diff=[int(x != full) for x in d2],
            w1=int(len(set(d1)) != 1),
            w2=int(len(set(d2)) != 1),
        ))

    n = len(rows)
    b1_all = np.array([x for r in rows for x in r["b1_diff"]])
    b2_all = np.array([x for r in rows for x in r["b2_diff"]])
    w1 = np.array([r["w1"] for r in rows])
    w2 = np.array([r["w2"] for r in rows])
    print(f"== Task 4A: original b3 gate, {n} batches ({miss} unmapped/missing eval) ==")
    print(f"  validate recomputed b=3 accept vs logged: {val_match}/{valid_val} agree "
          f"({val_match/valid_val:.4f})")
    print(f"  P(b'=1 decision != full b=3), overall = {b1_all.mean():.4f}  (n={len(b1_all)} subset-gates)")
    print(f"  P(b'=2 decision != full b=3), overall = {b2_all.mean():.4f}  (n={len(b2_all)} subset-gates)")
    print(f"  within-b'=1 disagreement (3 single gates non-unanimous) = {w1.mean():.4f}  (n={n})")
    print(f"  within-b'=2 disagreement (3 pair gates non-unanimous)  = {w2.mean():.4f}  (n={n})")
    print("  per run:")
    csv_rows = [("seed", "n_batches", "P_flip_b1", "P_flip_b2", "within_b1", "within_b2")]
    for s in sorted(set(r["seed"] for r in rows)):
        rs = [r for r in rows if r["seed"] == s]
        p1 = np.mean([x for r in rs for x in r["b1_diff"]])
        p2 = np.mean([x for r in rs for x in r["b2_diff"]])
        ww1 = np.mean([r["w1"] for r in rs])
        ww2 = np.mean([r["w2"] for r in rs])
        print(f"    s{s}: n={len(rs):3d}  P_flip b'=1={p1:.4f}  b'=2={p2:.4f}  "
              f"within b'=1={ww1:.4f}  b'=2={ww2:.4f}")
        csv_rows.append((s, len(rs), round(p1, 4), round(p2, 4), round(ww1, 4), round(ww2, 4)))

    # write instability-vs-n CSV
    with open("analysis/verification_postswap_task4_instability.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["bprime", "P_decision_differs_vs_b3", "within_bprime_disagreement", "n_subset_gates", "n_batches"])
        w.writerow([1, round(b1_all.mean(), 4), round(w1.mean(), 4), len(b1_all), n])
        w.writerow([2, round(b2_all.mean(), 4), round(w2.mean(), 4), len(b2_all), n])

    # ---- 4C: b=1 baselines ----
    print("\n== Task 4C: b=1 baselines ==")
    b1runs = load_logs(1)
    for seed in sorted(b1runs):
        cyc = b1runs[seed]
        accs, logged = [], []
        ex_accept = {}  # example_id -> list of recomputed accept bools
        for it, c in cyc.items():
            if len(c["before"]) != 1 or len(c["after"]) != 1:
                continue
            a = accept(c["after"], c["before"])
            accs.append(int(a))
            if c["logged"] is not None:
                logged.append(int(c["logged"] == a))
            if c["mb_ids"]:
                ex_accept.setdefault(c["mb_ids"][0], []).append(a)
        rate = np.mean(accs) if accs else float("nan")
        vmatch = (np.mean(logged) if logged else float("nan"))
        # same-input (example-id) repeat disagreement: example ids appearing in >=2 cycles
        rep = [ids for ids in ex_accept.values() if len(ids) >= 2]
        rep_dis = np.mean([0 if len(set(v)) == 1 else 1 for v in rep]) if rep else float("nan")
        print(f"  seed{seed}_b1: n_cycles={len(accs)}  accept_rate={rate:.4f}  "
              f"(recomputed==logged: {vmatch:.4f})")
        print(f"    same-example-id repeat disagreement: {rep_dis:.4f}  "
              f"(over {len(rep)} example-ids sampled in >=2 cycles; parent/child differ across cycles)")

    print("\n== Task 4B: INFEASIBLE offline ==")
    print("  Ranking the 3 batch-swap sibling draws by own-margin on b'=1/b'=2 subsets needs")
    print("  per-example scores of the R_B/R_Bp child DRAWS. batch_swap_v2_run.py:230-235 wrote")
    print("  only the sums (capture_traces=False); the per-example vectors exist in no file.")
    print("  Regenerating them = live LM calls (forbidden). No 4B numbers reported.")


if __name__ == "__main__":
    main()
