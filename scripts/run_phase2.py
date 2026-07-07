"""Phase-2 paired-A/B runner: one GEPA run under a chosen minibatch sampler.

Identical to run_baseline.py in EVERY respect (models, split, budget, seed, logging) EXCEPT
the sampler:
  --sampler uniform       -> default EpochShuffledBatchSampler (the baseline behavior)
  --sampler tractability  -> TractabilitySampler (Phase-1 survivor as a live curriculum)

Logs to logs/phase2/ (the frozen baseline corpus in logs/ is never touched). Captures the
returned GEPAResult so the best program is stored in the sidecar for the OOD endpoint.

Run from repo root (key from .env):
    .venv/bin/python scripts/run_phase2.py --seed 0 --sampler tractability --max-metric-calls 2500
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
    sys.exit("ERROR: OPENAI_API_KEY is not set. Paste your real key into .env, then re-run.")

from gepa import optimize  # noqa: E402
from gepa.adapters.default_adapter.default_adapter import DefaultAdapter  # noqa: E402
from gepa.lm import LM  # noqa: E402

from gepa_si.ifbench_eval import IFConstraintEvaluator  # noqa: E402
from gepa_si import ifrlvr_data  # noqa: E402
from gepa_si.ifrlvr_data import load_faithful_splits  # noqa: E402
from gepa_si.si_event_logger import SIEventLogger  # noqa: E402
from gepa_si.tractability_sampler import TractabilitySampler  # noqa: E402

TASK_LM = "openai/gpt-4.1-mini"
REFLECTION_LM = "openai/gpt-4.1"
MAX_METRIC_CALLS = 2500
LOG_DIR = "logs/phase2"

# Same seed candidate as the baseline corpus — only the sampler differs.
SEED_CANDIDATE = {
    "system_prompt": (
        "You are a helpful assistant. Read the user's request carefully and follow "
        "every instruction and formatting constraint exactly."
    )
}


def _best_program_text(result) -> tuple[int | None, str]:
    bc = result.best_candidate
    if isinstance(bc, dict):
        text = bc.get("system_prompt") or next(iter(bc.values()))
    else:
        text = bc
    return getattr(result, "best_idx", None), text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--b", "--reflection-minibatch-size", dest="b", type=int, default=3)
    ap.add_argument("--sampler", choices=["uniform", "tractability"], required=True)
    ap.add_argument("--max-metric-calls", type=int, default=MAX_METRIC_CALLS)
    args = ap.parse_args()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    arm = args.sampler
    stem = f"phase2_{arm}_seed{args.seed}_b{args.b}_{ts}"
    os.makedirs(LOG_DIR, exist_ok=True)
    log_path = f"{LOG_DIR}/{stem}.jsonl"
    config_path = f"{LOG_DIR}/{stem}.config.json"
    run_id = f"phase2_{arm}_seed{args.seed}_b{args.b}"
    if os.path.exists(log_path):
        sys.exit(f"ERROR: log file already exists: {log_path}")

    trainset, valset = load_faithful_splits()

    config = {
        "run_id": run_id,
        "arm": arm,
        "sampler": arm,
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

    adapter = DefaultAdapter(model=TASK_LM, evaluator=IFConstraintEvaluator())
    reflection_lm = LM(REFLECTION_LM)
    logger = SIEventLogger(log_path, run_id=run_id)

    # The ONLY difference between arms:
    if arm == "uniform":
        sampler_kwargs = dict(batch_sampler="epoch_shuffled", reflection_minibatch_size=args.b)
    else:
        sampler_kwargs = dict(
            batch_sampler=TractabilitySampler(minibatch_size=args.b, seed=args.seed),
            reflection_minibatch_size=None,
        )

    result = None
    try:
        result = optimize(
            seed_candidate=SEED_CANDIDATE,
            trainset=trainset,
            valset=valset,
            adapter=adapter,
            task_lm=None,
            evaluator=None,
            reflection_lm=reflection_lm,
            max_metric_calls=args.max_metric_calls,
            seed=args.seed,
            display_progress_bar=True,
            callbacks=[logger],
            **sampler_kwargs,
        )
    finally:
        logger.close()

    _report(log_path, config_path, adapter, reflection_lm, result)


def _report(log_path, config_path, adapter, reflection_lm, result) -> None:
    records = [json.loads(l) for l in open(log_path, encoding="utf-8") if l.strip()]
    counts = Counter(r.get("event") for r in records)
    end = next((r for r in records if r.get("event") == "optimization_end"), None)

    t_cost = getattr(adapter._lm, "total_cost", 0.0) or 0.0
    r_cost = getattr(reflection_lm, "total_cost", 0.0) or 0.0
    best_idx, best_prompt = (None, "")
    if result is not None:
        best_idx, best_prompt = _best_program_text(result)

    results = {
        "completed": True,
        "arm": (json.load(open(config_path)).get("arm")),
        "sampler": (json.load(open(config_path)).get("sampler")),
        "task_usd": t_cost,
        "reflection_usd": r_cost,
        "total_usd": t_cost + r_cost,
        "task_tokens_in": getattr(adapter._lm, "total_tokens_in", 0),
        "task_tokens_out": getattr(adapter._lm, "total_tokens_out", 0),
        "reflection_tokens_in": getattr(reflection_lm, "total_tokens_in", 0),
        "reflection_tokens_out": getattr(reflection_lm, "total_tokens_out", 0),
        "accepts": counts.get("candidate_accepted", 0),
        "rejects": counts.get("candidate_rejected", 0),
        "total_metric_calls": end.get("total_metric_calls") if end else None,
        "total_iterations": end.get("total_iterations") if end else None,
        "best_candidate_idx": best_idx,
        "best_system_prompt": best_prompt,
    }
    with open(config_path, encoding="utf-8") as fh:
        config = json.load(fh)
    config["results"] = results
    with open(config_path, "w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2)

    print(f"\n========== PHASE-2 RUN REPORT ({log_path}) ==========")
    print(f"  arm={results['arm']}  accepts={results['accepts']} rejects={results['rejects']}  "
          f"best_idx={best_idx}")
    print(f"  total_metric_calls={results['total_metric_calls']} iterations={results['total_iterations']}")
    print(f"  cost: task ${t_cost:.4f} + reflection ${r_cost:.4f} = ${t_cost + r_cost:.4f}")
    print("=" * 52)


if __name__ == "__main__":
    main()
