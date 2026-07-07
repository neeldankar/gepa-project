"""Reusable faithful baseline runner (offline-screen corpus, part 2).

One GEPA optimization run on the shared 150/150 IF-RLVR split (IFEvalG-verified). All
screen baselines reuse this script and differ ONLY by --seed (which drives both minibatch
shuffling and candidate selection). Builds the task adapter and reflection LM explicitly
so we can read exact per-side cost/tokens after the run.

Log hygiene: one clean file per run (timestamped); refuses to append to an existing file.
A sidecar `.config.json` makes the corpus self-describing for the later scorer/screen task.

Run from repo root (key loaded from .env):
    .venv/bin/python scripts/run_baseline.py --seed 0 --b 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime
from importlib.metadata import version

from dotenv import load_dotenv

load_dotenv()

_key = os.environ.get("OPENAI_API_KEY", "").strip()
if not _key or _key == "REPLACE_ME":
    sys.exit(
        "ERROR: OPENAI_API_KEY is not set. Paste your real key into the .env file "
        "in the repo root, then re-run. The key is loaded from .env and never hardcoded."
    )

from gepa import optimize  # noqa: E402
from gepa.adapters.default_adapter.default_adapter import DefaultAdapter  # noqa: E402
from gepa.lm import LM  # noqa: E402

from gepa_si.ifbench_eval import IFConstraintEvaluator  # noqa: E402
from gepa_si import ifrlvr_data  # noqa: E402
from gepa_si.ifrlvr_data import load_faithful_splits  # noqa: E402
from gepa_si.si_event_logger import SIEventLogger  # noqa: E402

TASK_LM = "openai/gpt-4.1-mini"
REFLECTION_LM = "openai/gpt-4.1"
# Modest pilot budget: we want the events-per-run rate and the actual cost, NOT a
# maxed-out run. Tune up for the real screen.
MAX_METRIC_CALLS_PILOT = 1000

SEED_CANDIDATE = {
    "system_prompt": (
        "You are a helpful assistant. Read the user's request carefully and follow "
        "every instruction and formatting constraint exactly."
    )
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--b", "--reflection-minibatch-size", dest="b", type=int, default=3)
    ap.add_argument("--max-metric-calls", type=int, default=MAX_METRIC_CALLS_PILOT)
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = f"baseline_seed{args.seed}_b{args.b}_{ts}"
    log_path = f"logs/{stem}.jsonl"
    config_path = f"logs/{stem}.config.json"
    run_id = f"baseline_seed{args.seed}_b{args.b}"

    os.makedirs("logs", exist_ok=True)
    if os.path.exists(log_path):  # one run = one fresh file
        sys.exit(f"ERROR: log file already exists: {log_path}")

    trainset, valset = load_faithful_splits()

    # Self-describing sidecar so the scorer/screen can group runs without guessing.
    config = {
        "run_id": run_id,
        "seed": args.seed,
        "b": args.b,
        "n_train": len(trainset),
        "n_val": len(valset),
        "split_seed": ifrlvr_data.SEED,
        "task_lm": TASK_LM,
        "reflection_lm": REFLECTION_LM,
        "max_metric_calls": args.max_metric_calls,
        "timestamp": ts,
        "gepa_version": version("gepa"),
        "log_path": log_path,
    }
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)
    print(f"Config: {config_path}\n{json.dumps(config, indent=2)}")

    # Explicit adapter + reflection LM → we keep handles for exact cost/token accounting.
    adapter = DefaultAdapter(model=TASK_LM, evaluator=IFConstraintEvaluator())
    reflection_lm = LM(REFLECTION_LM)

    logger = SIEventLogger(log_path, run_id=run_id)
    try:
        optimize(
            seed_candidate=SEED_CANDIDATE,
            trainset=trainset,
            valset=valset,
            adapter=adapter,
            task_lm=None,
            evaluator=None,
            reflection_lm=reflection_lm,
            reflection_minibatch_size=args.b,
            max_metric_calls=args.max_metric_calls,
            seed=args.seed,
            display_progress_bar=True,
            callbacks=[logger],
        )
    finally:
        logger.close()

    _report(log_path, config_path, adapter, reflection_lm)


def _report(log_path: str, config_path: str, adapter, reflection_lm) -> None:
    records = [json.loads(line) for line in open(log_path, encoding="utf-8") if line.strip()]
    counts = Counter(r.get("event") for r in records)
    end = next((r for r in records if r.get("event") == "optimization_end"), None)

    t_cost = getattr(adapter._lm, "total_cost", 0.0) or 0.0
    t_in = getattr(adapter._lm, "total_tokens_in", 0)
    t_out = getattr(adapter._lm, "total_tokens_out", 0)
    r_cost = getattr(reflection_lm, "total_cost", 0.0) or 0.0
    r_in = getattr(reflection_lm, "total_tokens_in", 0)
    r_out = getattr(reflection_lm, "total_tokens_out", 0)

    results = {
        "completed": True,
        "task_usd": t_cost,
        "reflection_usd": r_cost,
        "total_usd": t_cost + r_cost,
        "task_tokens_in": t_in,
        "task_tokens_out": t_out,
        "reflection_tokens_in": r_in,
        "reflection_tokens_out": r_out,
        "n_reflective_dataset_built": counts.get("reflective_dataset_built", 0),
        "accepts": counts.get("candidate_accepted", 0),
        "rejects": counts.get("candidate_rejected", 0),
        "total_metric_calls": end.get("total_metric_calls") if end else None,
        "total_iterations": end.get("total_iterations") if end else None,
    }
    # Persist results into the sidecar so a batch driver reads cost/counts robustly
    # (no stdout parsing) and the run is discoverable as completed for resume.
    with open(config_path, encoding="utf-8") as fh:
        config = json.load(fh)
    config["results"] = results
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)

    print(f"\n========== RUN REPORT ({log_path}) ==========")
    print(f"records: {len(records)}")
    print("event counts:")
    for event, n in counts.most_common():
        print(f"  {event:28s} {n}")
    print("\nkey numbers:")
    print(f"  reflective_dataset_built (per-run screen sample size): {results['n_reflective_dataset_built']}")
    print(f"  candidate_accepted: {results['accepts']}  candidate_rejected: {results['rejects']}")
    print(f"  reflection calls (proposal_end events): {counts.get('proposal_end', 0)}")
    print(f"  total_metric_calls (task evals): {results['total_metric_calls']}")
    print(f"  total_iterations: {results['total_iterations']}")
    print("\ncost / tokens:")
    print(f"  task LM      ({TASK_LM:>20s}): ${t_cost:.4f}  tokens in/out {t_in}/{t_out}")
    print(f"  reflection LM({REFLECTION_LM:>20s}): ${r_cost:.4f}  tokens in/out {r_in}/{r_out}")
    print(f"  TOTAL: ${t_cost + r_cost:.4f}")
    print("=" * 52)


if __name__ == "__main__":
    main()
