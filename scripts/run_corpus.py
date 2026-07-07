"""Sequential batch driver for the baseline corpus (offline-screen corpus, part 2).

Runs 10 jobs (8 baselines b=3 seeds 0–7, then 2 diagnostics b=1 seeds 0–1) at
max_metric_calls=2500, each via scripts/run_baseline.py. Resumable (skips jobs whose
completed sidecar already exists) and cost-capped (stops before any run that would push
the cumulative corpus spend over $32).

    .venv/bin/python scripts/run_corpus.py        # run in background (~2.5–3h)

Re-running after any interruption continues where it left off.
"""

from __future__ import annotations

import glob
import json
import subprocess
import sys

MAX_METRIC_CALLS = 2500
COST_CAP_USD = 33.0  # bumped from 32.0: seed1_b1 ran during auto-recovery, so the final
# b1 seed0 run (~$3.2) needs ~2¢ more headroom. Recorded cumulative ends ~$32.1; actual
# account spend ~$36-37, well under the ~$42 balance.
SEED_RUN_ESTIMATE_USD = 3.0  # used only until we have an observed average
VENV_PY = ".venv/bin/python"

# Order: 8 primary baselines (b=3) FIRST, then 2 b=1 diagnostics LAST, so if the cap
# ever trims, it trims a diagnostic.
JOBS = [(3, s) for s in range(8)] + [(1, s) for s in range(2)]


def _completed_sidecar(seed: int, b: int) -> dict | None:
    """Newest completed sidecar matching (seed, b, MAX_METRIC_CALLS), if any."""
    matches = []
    for path in glob.glob(f"logs/baseline_seed{seed}_b{b}_*.config.json"):
        try:
            with open(path, encoding="utf-8") as fh:
                cfg = json.load(fh)
        except (json.JSONDecodeError, OSError) as e:
            # A truncated/corrupt sidecar (e.g. from a mid-write power cut) must degrade
            # to "re-run this one", never crash the whole pre-scan.
            print(f"[warn] ignoring unreadable sidecar {path}: {e!r}")
            continue
        if cfg.get("max_metric_calls") == MAX_METRIC_CALLS and cfg.get("results", {}).get("completed"):
            matches.append((cfg.get("timestamp", ""), cfg))
    if not matches:
        return None
    return max(matches, key=lambda t: t[0])[1]


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Print skip/run/cap decisions without making any API calls.")
    dry = ap.parse_args().dry_run
    if dry:
        print("=== DRY RUN — no subprocesses launched, no API calls ===")

    cumulative = 0.0
    completed_costs: list[float] = []
    failures: list[tuple[int, int]] = []

    # Seed cumulative from already-completed runs (resume) — pre-scan all jobs.
    for b, seed in JOBS:
        cfg = _completed_sidecar(seed, b)
        if cfg:
            completed_costs.append(cfg["results"]["total_usd"])
            cumulative += cfg["results"]["total_usd"]
    if completed_costs:
        print(f"[resume] {len(completed_costs)} run(s) already complete; "
              f"cumulative ${cumulative:.4f}")

    for b, seed in JOBS:
        tag = f"seed{seed}_b{b}"
        cfg = _completed_sidecar(seed, b)
        if cfg:
            print(f"[skip] {tag} already complete — run ${cfg['results']['total_usd']:.4f} "
                  f"| cumulative ${cumulative:.4f}")
            continue

        # Cost cap: predict next run from observed average (fallback to seed estimate).
        predicted = (sum(completed_costs) / len(completed_costs)) if completed_costs else SEED_RUN_ESTIMATE_USD
        if cumulative + predicted > COST_CAP_USD:
            print(f"[cap] STOP before {tag}: cumulative ${cumulative:.4f} + predicted "
                  f"${predicted:.4f} would exceed ${COST_CAP_USD:.2f}. Halting batch.")
            break

        if dry:
            print(f"[would-run] {tag} (predicted ~${predicted:.2f}, cumulative ${cumulative:.4f})")
            continue

        print(f"\n[run] {tag} (predicted ~${predicted:.2f}, cumulative ${cumulative:.4f}) ...")
        proc = subprocess.run(
            [VENV_PY, "scripts/run_baseline.py", "--seed", str(seed), "--b", str(b),
             "--max-metric-calls", str(MAX_METRIC_CALLS)],
        )
        if proc.returncode != 0:
            print(f"[fail] {tag} exited {proc.returncode} — continuing (re-run driver to retry).")
            failures.append((seed, b))
            continue

        cfg = _completed_sidecar(seed, b)
        if cfg is None:
            print(f"[fail] {tag} produced no completed sidecar — continuing.")
            failures.append((seed, b))
            continue
        r = cfg["results"]
        completed_costs.append(r["total_usd"])
        cumulative += r["total_usd"]
        print(f"[done] {tag} | #SI={r['n_reflective_dataset_built']} "
              f"accepts={r['accepts']} rejects={r['rejects']} | run ${r['total_usd']:.4f} "
              f"| cumulative ${cumulative:.4f}")

    print(f"\n===== batch finished. cumulative ${cumulative:.4f} of ${COST_CAP_USD:.2f} cap. "
          f"failures: {failures or 'none'} =====\n")

    # Final corpus summary.
    if not dry:
        subprocess.run([VENV_PY, "scripts/corpus_summary.py"])


if __name__ == "__main__":
    main()
