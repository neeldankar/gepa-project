"""STAGED HotpotQA baseline runner (Part-3 viable benchmark) — generates real SI to eyeball.

NOT a measurement run: smallest sensible split + modest budget, uniform sampler, only to see what
HotpotQA side-information looks like on a non-IFBench task. Mirrors scripts/run_baseline.py.

Pipeline ($0 retrieval): load cached HotpotQA-distractor via Arrow-direct (HF script-load is broken);
per example, BM25 (rank_bm25) over its 10 inline passages → top-k context (local, no API); a
DefaultAdapter answer program (task LM gpt-4.1-mini) scored by token-F1; reflection LM gpt-4.1
optimizes the answer prompt. Logs to logs/hotpot/.

⚠️ THIS SCRIPT MAKES OPENAI API CALLS WHEN RUN. It is staged behind the Phase-1.x cost gate — do not
run without explicit go-ahead. Retrieval/loading are $0; the optimize() call is the spend.

Run (only after go-ahead):
    .venv/bin/python scripts/run_hotpot_baseline.py --n-train 40 --n-val 40 --max-metric-calls 300
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime
from importlib.metadata import version

from dotenv import load_dotenv

load_dotenv()

TASK_LM = "openai/gpt-4.1-mini"
REFLECTION_LM = "openai/gpt-4.1"
TOPK = 4
SEED_CANDIDATE = {
    "system_prompt": (
        "You are a careful multi-hop question answerer. Read the provided context passages, reason "
        "across them, and answer the question with a short, exact span or yes/no. Output only the answer."
    )
}
_TOK = re.compile(r"[a-z0-9]+")


def _arrow(split: str) -> str:
    base = os.path.expanduser("~/.cache/huggingface/datasets/hotpotqa___hotpot_qa")
    hits = glob.glob(f"{base}/**/hotpot_qa-{split}*.arrow", recursive=True)
    if not hits:
        sys.exit(f"ERROR: cached HotpotQA {split} arrow not found (expected under {base})")
    return sorted(hits)[0]


def _tok(s: str):
    return _TOK.findall(s.lower())


def load_hotpot(split: str, n: int, seed: int = 0):
    """Arrow-direct load + BM25 retrieval baked into each example's input (deterministic, $0)."""
    from datasets import Dataset
    from rank_bm25 import BM25Okapi
    ds = Dataset.from_file(_arrow(split)).shuffle(seed=seed).select(range(n))
    items = []
    for ex in ds:
        titles, sents = ex["context"]["title"], ex["context"]["sentences"]
        docs = [" ".join(s) for s in sents]
        bm = BM25Okapi([_tok(t + " " + d) for t, d in zip(titles, docs)])
        order = sorted(range(len(titles)), key=lambda i: -bm.get_scores(_tok(ex["question"]))[i])[:TOPK]
        ctx = "\n\n".join(f"[{titles[i]}] {docs[i]}" for i in order)
        items.append({
            "input": f"Context:\n{ctx}\n\nQuestion: {ex['question']}\nAnswer:",
            "additional_context": {}, "answer": ex["answer"],
            "gold_titles": list(ex["supporting_facts"]["title"]),
            "retrieved_titles": [titles[i] for i in order],
        })
    return items


class HotpotF1:
    """Token-F1 answer evaluator + retrieval-recall SI (the eyeball target)."""
    def __call__(self, data, response: str):
        from gepa.adapters.default_adapter.default_adapter import EvaluationResult
        g, p = set(_tok(data["answer"])), set(_tok(response or ""))
        f1 = (2 * len(g & p) / (len(g) + len(p))) if (g and p) else 0.0
        em = float(" ".join(_tok(data["answer"])) == " ".join(_tok(response or "")))
        recall = len(set(data["gold_titles"]) & set(data["retrieved_titles"])) / max(1, len(set(data["gold_titles"])))
        fb = (f"answer F1={f1:.2f} EM={em:.0f}; gold='{data['answer']}'; "
              f"gold_docs={data['gold_titles']} retrieved={data['retrieved_titles']} recall={recall:.2f}")
        return EvaluationResult(score=f1, feedback=fb, objective_scores={"f1": f1, "em": em, "doc_recall": recall})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-train", type=int, default=40)
    ap.add_argument("--n-val", type=int, default=40)
    ap.add_argument("--b", type=int, default=3)
    ap.add_argument("--max-metric-calls", type=int, default=300)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    if not os.environ.get("OPENAI_API_KEY", "").strip():
        sys.exit("ERROR: OPENAI_API_KEY not set.")

    from gepa import optimize
    from gepa.adapters.default_adapter.default_adapter import DefaultAdapter
    from gepa.lm import LM

    trainset = load_hotpot("train", args.n_train, args.seed)
    valset = load_hotpot("validation", args.n_val, args.seed)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("logs/hotpot", exist_ok=True)
    stem = f"hotpot_uniform_seed{args.seed}_b{args.b}_{ts}"
    log_path, config_path = f"logs/hotpot/{stem}.jsonl", f"logs/hotpot/{stem}.config.json"

    from gepa_si.si_event_logger import SIEventLogger
    adapter = DefaultAdapter(model=TASK_LM, evaluator=HotpotF1())
    reflection_lm = LM(REFLECTION_LM)
    logger = SIEventLogger(log_path, run_id=stem)
    json.dump({"benchmark": "hotpotqa_distractor", "n_train": args.n_train, "n_val": args.n_val,
               "b": args.b, "max_metric_calls": args.max_metric_calls, "task_lm": TASK_LM,
               "reflection_lm": REFLECTION_LM, "topk": TOPK, "timestamp": ts,
               "gepa_version": version("gepa"), "log_path": log_path},
              open(config_path, "w"), indent=2)
    try:
        optimize(seed_candidate=SEED_CANDIDATE, trainset=trainset, valset=valset, adapter=adapter,
                 reflection_lm=reflection_lm, reflection_minibatch_size=args.b,
                 max_metric_calls=args.max_metric_calls, seed=args.seed,
                 display_progress_bar=True, callbacks=[logger])
    finally:
        logger.close()
    counts = Counter(json.loads(l).get("event") for l in open(log_path) if l.strip())
    print(f"done: {dict(counts)}  cost: task ${getattr(adapter._lm,'total_cost',0):.4f} "
          f"+ reflection ${getattr(reflection_lm,'total_cost',0):.4f}")


if __name__ == "__main__":
    main()
