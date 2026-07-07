"""Phase-2 pair driver: run (uniform, tractability) GEPA pairs + OOD eval, resumable & capped.

Mirrors run_corpus.py discipline: skips already-completed runs (sidecar with results.completed),
caps cumulative cost, runs the OOD endpoint eval after each run.

  --seeds 0          validation pair only (both arms, seed 0), then STOP
  --seeds 1-7        the rest, after go-ahead
  --seeds 0-7        full set

Run: HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/run_phase2_corpus.py --seeds 0
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import subprocess
import sys

VENV_PY = ".venv/bin/python"
ARMS = ["uniform", "tractability"]
B = 3
MAX_METRIC_CALLS = 2500
COST_CAP_USD = 110.0
RUN_ESTIMATE_USD = 4.0
LOG_DIR = "logs/phase2"


def _parse_seeds(spec: str) -> list[int]:
    out = []
    for part in spec.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def _completed(arm: str, seed: int) -> dict | None:
    matches = []
    for path in glob.glob(f"{LOG_DIR}/phase2_{arm}_seed{seed}_b{B}_*.config.json"):
        try:
            cfg = json.load(open(path, encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if cfg.get("max_metric_calls") == MAX_METRIC_CALLS and cfg.get("results", {}).get("completed"):
            matches.append((cfg.get("timestamp", ""), path, cfg))
    if not matches:
        return None
    _, path, cfg = max(matches, key=lambda t: t[0])
    return {"path": path, "cfg": cfg}


def _run_one(arm: str, seed: int, cumulative: float, completed_costs: list[float]) -> float:
    tag = f"{arm}_seed{seed}"
    done = _completed(arm, seed)
    if done:
        cost = done["cfg"].get("results", {}).get("total_usd", 0.0)
        print(f"[skip] {tag} already completed (${cost:.4f})")
        _eval_endpoint(done["path"])
        return cost

    predicted = (sum(completed_costs) / len(completed_costs)) if completed_costs else RUN_ESTIMATE_USD
    if cumulative + predicted > COST_CAP_USD:
        sys.exit(f"[cap] STOP before {tag}: ${cumulative:.2f} + ${predicted:.2f} > ${COST_CAP_USD:.2f}")

    print(f"\n=== RUN {tag} (cumulative ${cumulative:.2f}) ===")
    proc = subprocess.run(
        [VENV_PY, "scripts/run_phase2.py", "--seed", str(seed), "--sampler", arm,
         "--max-metric-calls", str(MAX_METRIC_CALLS)],
    )
    if proc.returncode != 0:
        sys.exit(f"[error] {tag} exited {proc.returncode}; stopping for inspection.")
    done = _completed(arm, seed)
    if not done:
        sys.exit(f"[error] {tag} produced no completed sidecar; stopping.")
    _eval_endpoint(done["path"])
    return done["cfg"].get("results", {}).get("total_usd", 0.0)


def _eval_endpoint(config_path: str) -> None:
    proc = subprocess.run([VENV_PY, "scripts/eval_ood.py", "--config", config_path])
    if proc.returncode != 0:
        sys.exit(f"[error] OOD eval failed for {config_path}; stopping.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0", help="e.g. '0', '1-7', '0-7'")
    args = ap.parse_args()
    seeds = _parse_seeds(args.seeds)

    cumulative = 0.0
    completed_costs: list[float] = []
    for seed in seeds:
        for arm in ARMS:
            c = _run_one(arm, seed, cumulative, completed_costs)
            cumulative += c
            if c > 0:
                completed_costs.append(c)

    print(f"\n=== driver done: seeds={seeds} cumulative ${cumulative:.2f} ===")
    if seeds == [0]:
        print("VALIDATION PAIR complete. Inspect, then run --seeds 1-7 after go-ahead.")


if __name__ == "__main__":
    main()
