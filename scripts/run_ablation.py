"""Feedback-ablation experiment — Stages 1-2 (PAID: gpt-4.1 proposer + gpt-4.1-mini gate).

Byte-fidelity-proven reconstruction of the proposer input; three arms (i intact / ii feedback-deleted /
iii generic) + (i') seed-repeat; pointwise gate = child minibatch sum > parent minibatch sum (both
re-evaled today). Hard spend tripwire ($55). Logs every call to analysis/ablation/calls.csv.

  .venv/bin/python scripts/run_ablation.py --smoke   # 1 batch (~$0.05), validate pipeline
  .venv/bin/python scripts/run_ablation.py           # full 150 batches (~$8-9, cap $60)
"""
from __future__ import annotations

import csv
import json
import os
import random
import sys

from dotenv import load_dotenv

load_dotenv()
if not os.environ.get("OPENAI_API_KEY", "").strip():
    sys.exit("ERROR: OPENAI_API_KEY not set")

from gepa.lm import LM
from gepa.adapters.default_adapter.default_adapter import DefaultAdapter
from gepa.strategies.instruction_proposal import InstructionProposalSignature
from gepa_si.ifbench_eval import IFConstraintEvaluator
from gepa_si.ifrlvr_data import load_faithful_splits
from gepa_si.screen.corpus_io import discover_runs, _load

SMOKE = "--smoke" in sys.argv
OUT = "analysis/ablation"
GENERIC = "This example's output did not meet requirements."
SPEND_CAP = 55.0
PROPOSER, TASK = "openai/gpt-4.1", "openai/gpt-4.1-mini"

TEMPLATE = """I provided an assistant with the following instructions to perform a task for me:
```
<curr_param>
```

The following are examples of different task inputs provided to the assistant along with the assistant's response for each of them, and some feedback on how the assistant's response could be better:
```
<side_info>
```

Your task is to write a new instruction for the assistant.

Read the inputs carefully and identify the input format and infer detailed task description about the task I wish to solve with the assistant.

Read all the assistant responses and the corresponding feedback. Identify all niche and domain specific factual information about the task and include it in the instruction, as a lot of it may not be available to the assistant in the future. The assistant may have utilized a generalizable strategy to solve the task, if so, include that in the instruction as well.

Provide the new instructions within ``` blocks."""


def render_example(d, n):
    s = f"# Example {n}\n"
    for k, v in d.items():
        s += f"## {k}\n{str(v).strip()}\n\n"
    return s


def build_prompt(curr, examples):
    side = "\n\n".join(render_example(d, i + 1) for i, d in enumerate(examples))
    return TEMPLATE.replace("<curr_param>", curr).replace("<side_info>", side)


def arm_examples(exs, arm):
    out = []
    for e in exs:
        if arm == "i":
            out.append({"Inputs": e["Inputs"], "Generated Outputs": e["Generated Outputs"], "Feedback": e["Feedback"]})
        elif arm == "ii":
            out.append({"Inputs": e["Inputs"], "Generated Outputs": e["Generated Outputs"]})
        elif arm == "iii":
            out.append({"Inputs": e["Inputs"], "Generated Outputs": e["Generated Outputs"], "Feedback": GENERIC})
    return out


def extract_curr(sysp):
    import re
    m = re.search(r"instructions to perform a task for me:\n```\n(.*?)\n```\n", sysp, re.S)
    return m.group(1)


# ---- load frozen batch material: 3 example dicts + parent instr + mb_ids per (seed, iteration) ----
def load_batches():
    by = {}
    for cfg in discover_runs():
        if cfg["b"] != 3:
            continue
        recs = _load(cfg["log_path"])
        rdb = {r["iteration"]: r for r in recs if r.get("event") == "reflective_dataset_built"}
        mbs = {r["iteration"]: r for r in recs if r.get("event") == "minibatch_sampled"}
        for r in recs:
            if r.get("event") != "proposal_end":
                continue
            it = r["iteration"]
            if it not in rdb or it not in mbs:
                continue
            ds = rdb[it].get("dataset") or {}
            comp = (rdb[it].get("components") or list(ds.keys()))[0]
            by[(cfg["seed"], it)] = {
                "examples": ds[comp],
                "curr": extract_curr(r["prompts"]["system_prompt"]),
                "mb_ids": list(mbs[it].get("minibatch_ids") or []),
                "sysp": r["prompts"]["system_prompt"],
            }
    return by


def main():
    trainset, _ = load_faithful_splits()
    batches = load_batches()
    sel = list(csv.DictReader(open(f"{OUT}/selected_batches.csv")))
    if SMOKE:
        sel = sel[:1]
    print(f"[{'SMOKE' if SMOKE else 'FULL'}] {len(sel)} batches")

    refl = LM(PROPOSER)
    adapter = DefaultAdapter(model=TASK, evaluator=IFConstraintEvaluator())

    calls_path = f"{OUT}/calls{'_smoke' if SMOKE else ''}.csv"
    fh = open(calls_path, "w", newline="")
    cw = csv.writer(fh)
    cw.writerow(["batch_id", "seed", "iteration", "arm", "call_idx", "child_score_sum", "parent_score_sum_today",
                 "parent_score_sum_logged", "accept_today", "child_instr_len", "cum_spend_usd"])

    def spend():
        return float(refl.total_cost) + float(adapter._lm.total_cost)

    def gate(instr, mb):
        ev = adapter.evaluate(mb, {"system_prompt": instr}, capture_traces=False)
        return list(ev.scores)

    n_done = 0
    for row in sel:
        key = (int(row["seed"]), int(row["iteration"]))
        if key not in batches:
            print(f"  MISSING {key}, skip"); continue
        bat = batches[key]; exs = bat["examples"]; mb_ids = bat["mb_ids"]
        mb = [trainset[t] for t in mb_ids]
        parent_today = gate(bat["curr"], mb); p_sum = sum(parent_today)
        # logged parent scores (cross-check) from before_scores
        p_logged = ""  # filled from corpus_io if needed; the log's before eval == parent scores
        arms = ["i", "ii", "iii"] + (["i_rep"] if int(row["in_seed_repeat"]) else [])
        random.Random(hash(key) & 0xffffffff).shuffle(arms)
        for ci, arm in enumerate(arms):
            base_arm = "i" if arm == "i_rep" else arm
            prompt = build_prompt(bat["curr"], arm_examples(exs, base_arm))
            raw = refl(prompt)
            child = InstructionProposalSignature.output_extractor(raw)["new_instruction"]
            child_scores = gate(child, mb); c_sum = sum(child_scores)
            cw.writerow([row["batch_id"], key[0], key[1], arm, ci, round(c_sum, 4), round(p_sum, 4),
                         p_logged, int(c_sum > p_sum), len(child), round(spend(), 4)])
            fh.flush()
            if spend() > SPEND_CAP:
                print(f"!!! SPEND TRIPWIRE ${spend():.2f} > ${SPEND_CAP} — ABORT after batch {n_done}")
                fh.close(); sys.exit(2)
        n_done += 1
        if n_done % 10 == 0 or SMOKE:
            print(f"  [{n_done}/{len(sel)}] spend ${spend():.4f}")
    fh.close()
    print(f"\nDONE {n_done} batches. proposer ${refl.total_cost:.4f} + task ${adapter._lm.total_cost:.4f} "
          f"= ${spend():.4f}  -> {calls_path}")


if __name__ == "__main__":
    main()
