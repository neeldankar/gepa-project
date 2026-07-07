"""Phase-2 primary endpoint: evaluate a run's BEST program on the IFBench OOD test split.

test_U(run) = mean per-instance score of the run's best candidate program on the 300 OOD
prompts (registry='ifbench'). Idempotent: caches to logs/phase2/<stem>.oodtest.json and skips
if present. Reuses DefaultAdapter.evaluate (batch task-LM completion + IFConstraintEvaluator).

Best program: prefer the sidecar's stored results.best_system_prompt (written by run_phase2);
fall back to reconstructing it from the log via optimization_end.best_candidate_idx.

Run: HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/eval_ood.py --config logs/phase2/<stem>.config.json
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np
from dotenv import load_dotenv

load_dotenv()

from gepa.adapters.default_adapter.default_adapter import DefaultAdapter  # noqa: E402

from gepa_si.ifbench_eval import IFConstraintEvaluator  # noqa: E402
from gepa_si.ifbench_ood_data import load_ood_testset  # noqa: E402
from gepa_si.screen.scorer_inputs import reconstruct_prompts  # noqa: E402

TASK_LM = "openai/gpt-4.1-mini"


def _best_prompt(config: dict) -> tuple[int | None, str]:
    res = config.get("results") or {}
    if res.get("best_system_prompt"):
        return res.get("best_candidate_idx"), res["best_system_prompt"]
    # fallback: reconstruct from the log
    log_path = config["log_path"]
    records = [json.loads(l) for l in open(log_path, encoding="utf-8") if l.strip()]
    end = next((r for r in records if r.get("event") == "optimization_end"), None)
    bidx = end.get("best_candidate_idx") if end else None
    prompts = reconstruct_prompts(log_path)
    if bidx is None or bidx not in prompts:
        sys.exit(f"ERROR: cannot recover best program for {log_path} (best_idx={bidx})")
    return bidx, prompts[bidx]


def eval_run(config_path: str, testset=None) -> dict:
    with open(config_path, encoding="utf-8") as fh:
        config = json.load(fh)
    stem = os.path.basename(config_path).replace(".config.json", "")
    out_path = os.path.join(os.path.dirname(config_path), f"{stem}.oodtest.json")
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as fh:
            cached = json.load(fh)
        print(f"[cached] {stem}: test_U={cached['test_U']:.4f}")
        return cached

    bidx, best_prompt = _best_prompt(config)
    if testset is None:
        testset = load_ood_testset()

    adapter = DefaultAdapter(model=TASK_LM, evaluator=IFConstraintEvaluator())
    res = adapter.evaluate(testset, {"system_prompt": best_prompt}, capture_traces=False)
    scores = [float(s) for s in res.scores]
    test_U = float(np.mean(scores))
    cost = getattr(adapter._lm, "total_cost", 0.0) or 0.0

    record = {
        "stem": stem,
        "run_id": config.get("run_id"),
        "seed": config.get("seed"),
        "arm": (config.get("results") or {}).get("arm") or config.get("arm"),
        "sampler": (config.get("results") or {}).get("sampler") or config.get("sampler"),
        "best_candidate_idx": bidx,
        "test_U": test_U,
        "n_test": len(scores),
        "scores": scores,                      # per-instance, for instance-level diagnostics
        "ood_eval_usd": cost,
        "task_lm": TASK_LM,
    }
    with open(out_path, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
    print(f"[eval] {stem}: test_U={test_U:.4f}  n={len(scores)}  cost=${cost:.4f}  -> {out_path}")
    return record


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="path to a run .config.json sidecar")
    args = ap.parse_args()
    eval_run(args.config)


if __name__ == "__main__":
    main()
