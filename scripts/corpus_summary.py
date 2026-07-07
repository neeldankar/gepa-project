"""Final summary over the baseline corpus (offline-screen corpus, part 2).

Reads all completed mm=2500 run sidecars + their logs and prints the corpus table,
totals, split-consistency check, static-id alignment, and the distinct-IFEvalG-constraint
count across all SI. Runnable anytime (the driver calls it at the end).

    .venv/bin/python scripts/corpus_summary.py
"""

from __future__ import annotations

import glob
import json
import re

MAX_METRIC_CALLS = 2500
STATIC_PATH = "logs/static_si_precompute.jsonl"

_ID_RE = re.compile(r"^[✓✗] \[([^\]]+)\]")


def _completed_sidecars(mm: int = MAX_METRIC_CALLS) -> list[dict]:
    out = []
    for path in glob.glob("logs/*.config.json"):
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
        if cfg.get("max_metric_calls") == mm and cfg.get("results", {}).get("completed"):
            out.append(cfg)
    # stable order: b desc (b=3 first), then seed
    return sorted(out, key=lambda c: (-c["b"], c["seed"]))


def _records(log_path: str) -> list[dict]:
    return [json.loads(l) for l in open(log_path, encoding="utf-8") if l.strip()]


def _strip_dup(key: str) -> str:
    # objective_scores keys disambiguate duplicates as "id#index"
    return key.split("#", 1)[0]


def main() -> None:
    cfgs = _completed_sidecars()
    if not cfgs:
        print(f"No completed runs with max_metric_calls={MAX_METRIC_CALLS} found.")
        return

    print(f"=== Baseline corpus ({len(cfgs)} completed runs, max_metric_calls={MAX_METRIC_CALLS}) ===\n")
    hdr = f"{'seed':>4} {'b':>2} {'#SI':>4} {'acc':>4} {'rej':>4} {'run_USD':>8}"
    print(hdr)
    print("-" * len(hdr))
    tot_si = tot_acc = tot_rej = 0
    tot_usd = 0.0
    constraint_ids: set[str] = set()
    splits = set()
    align_ok = True

    for cfg in cfgs:
        r = cfg["results"]
        print(f"{cfg['seed']:>4} {cfg['b']:>2} {r['n_reflective_dataset_built']:>4} "
              f"{r['accepts']:>4} {r['rejects']:>4} {r['total_usd']:>8.4f}")
        tot_si += r["n_reflective_dataset_built"]
        tot_acc += r["accepts"]
        tot_rej += r["rejects"]
        tot_usd += r["total_usd"]
        splits.add((cfg["n_train"], cfg["n_val"], cfg["split_seed"]))

        # distinct constraint ids + minibatch id-range alignment from this run's log
        for rec in _records(cfg["log_path"]):
            ev = rec.get("event")
            if ev == "reflective_dataset_built":
                for examples in (rec.get("dataset") or {}).values():
                    for ex in examples:
                        for line in (ex.get("Feedback") or "").splitlines():
                            m = _ID_RE.match(line)
                            if m:
                                constraint_ids.add(m.group(1))
            elif ev == "minibatch_sampled":
                ids = rec.get("minibatch_ids") or []
                if any((i < 0 or i > 149) for i in ids):
                    align_ok = False

    print("-" * len(hdr))
    print(f"\nTotals: runs={len(cfgs)}  reflective_dataset_built={tot_si} (screen sample size)"
          f"  accepts={tot_acc}  rejects={tot_rej}")
    print(f"Cumulative corpus USD: ${tot_usd:.4f}")

    # split consistency
    if len(splits) == 1:
        nt, nv, ss = next(iter(splits))
        print(f"\nSplit consistency: OK — all runs share n_train={nt}, n_val={nv}, split_seed={ss}")
    else:
        print(f"\nSplit consistency: MISMATCH — found {splits}")
    print(f"max_metric_calls consistency: all == {MAX_METRIC_CALLS} (by filter)")

    # static-id alignment
    static = _records(STATIC_PATH) if glob.glob(STATIC_PATH) else []
    static_ids = [r["example_id"] for r in static]
    static_ok = static_ids == list(range(len(static_ids))) and len(static_ids) == 150
    print(f"\nStatic precompute ids 0–149 contiguous: {static_ok} (n={len(static_ids)})")
    print(f"All runs' minibatch_ids within 0–149: {align_ok}")

    print(f"\nDistinct IFEvalG constraint ids across all SI: {len(constraint_ids)}")
    print("  sample:", sorted(constraint_ids)[:10])


if __name__ == "__main__":
    main()
