"""Batch-swap ablation (arm iv) — overnight PAID run (k=3, ~$36, cap via $55 tripwire).

Both arms via ONE fresh pipeline (parent run today): arm (i) reflects on B's fresh objects, arm (iv) on
B'`s fresh objects (same parent). Child gated on B. Checkpoint-resumable (append + skip completed batches),
retry <=3 on API errors, $55 tripwire.

  .venv/bin/python scripts/run_batch_swap.py --smoke   # 1 batch (~$0.10), validate fresh-parent e2e
  .venv/bin/python scripts/run_batch_swap.py           # full 382 batches
"""
from __future__ import annotations

import csv, json, os, random, re, sys, time
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
K = 3
SPEND_CAP = 55.0
CALLS = f"{OUT}/batch_swap_calls{'_smoke' if SMOKE else ''}.csv"
COMP = "system_prompt"

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


def build_prompt(curr, objs):
    def render(d, n):
        s = f"# Example {n}\n"
        for k, v in d.items():
            s += f"## {k}\n{str(v).strip()}\n\n"
        return s
    side = "\n\n".join(render(d, i + 1) for i, d in enumerate(objs))
    return TEMPLATE.replace("<curr_param>", curr).replace("<side_info>", side)


def retry(fn, what, n=3):
    for a in range(n):
        try:
            return fn()
        except Exception as e:
            print(f"  RETRY {a+1}/{n} on {what}: {e!r}", flush=True)
            time.sleep(3 * (a + 1))
    raise RuntimeError(f"FAILED after {n} retries: {what}")


def load_curr():
    """{(seed,iteration): parent instruction} from logged proposal_end system_prompt."""
    out = {}
    for cfg in discover_runs():
        if cfg["b"] != 3:
            continue
        for r in _load(cfg["log_path"]):
            if r.get("event") == "proposal_end":
                m = re.search(r"perform a task for me:\n```\n(.*?)\n```\n", r["prompts"]["system_prompt"], re.S)
                if m:
                    out[(cfg["seed"], r["iteration"])] = m.group(1)
    return out


def main():
    trainset, _ = load_faithful_splits()
    curr = load_curr()
    pairs = list(csv.DictReader(open(f"{OUT}/batch_swap_pairing.csv")))
    if SMOKE:
        pairs = pairs[:1]

    refl = LM("openai/gpt-4.1")
    adapter = DefaultAdapter(model="openai/gpt-4.1-mini", evaluator=IFConstraintEvaluator())

    def spend():
        return float(refl.total_cost) + float(adapter._lm.total_cost)

    # checkpoint: completed B_ids (6 rows = 2 arms x 3 draws)
    done = set()
    if os.path.exists(CALLS):
        c = list(csv.DictReader(open(CALLS)))
        cnt = {}
        for r in c:
            cnt[r["B_id"]] = cnt.get(r["B_id"], 0) + 1
        done = {b for b, n in cnt.items() if n >= 2 * K}
        fh = open(CALLS, "a", newline=""); cw = csv.writer(fh)
        print(f"resume: {len(done)} batches already complete")
    else:
        fh = open(CALLS, "w", newline=""); cw = csv.writer(fh)
        cw.writerow(["B_id", "Bprime_id", "arm", "draw", "child_sum", "parent_B_sum", "accept",
                     "margin", "cum_spend"])
    fh.flush()

    def objs_and_parentscore(examples, P):
        eb = retry(lambda: adapter.evaluate(examples, {COMP: P}, capture_traces=True), "eval")
        rd = adapter.make_reflective_dataset({COMP: P}, eb, [COMP])[COMP]
        return list(rd), float(sum(eb.scores))

    n_done = 0
    for row in pairs:
        Bid = row["B_id"]
        if Bid in done:
            continue
        key = (int(row["seed"]), int(row["iteration"]))
        if key not in curr:
            print(f"  no parent instr for {Bid}, skip"); continue
        P = curr[key]
        B_ex = [trainset[t] for t in json.loads(row["B_ids"])]
        Bp_ex = [trainset[t] for t in json.loads(row["Bprime_ids"])]
        obj_i, pB_sum = objs_and_parentscore(B_ex, P)          # arm (i) objects + gate baseline
        obj_iv, _ = objs_and_parentscore(Bp_ex, P)             # arm (iv) objects
        prompts = {"i": build_prompt(P, obj_i), "iv": build_prompt(P, obj_iv)}
        seq = [(arm, d) for arm in ("i", "iv") for d in range(K)]
        random.Random(hash(Bid) & 0xffffffff).shuffle(seq)
        for arm, d in seq:
            raw = retry(lambda: refl(prompts[arm]), f"proposer {Bid} {arm}{d}")
            child = InstructionProposalSignature.output_extractor(raw)["new_instruction"]
            cscore = retry(lambda: adapter.evaluate(B_ex, {COMP: child}, capture_traces=False), "gate")
            c_sum = float(sum(cscore.scores))
            cw.writerow([Bid, row["Bprime_id"] if "Bprime_id" in row else f"s{row['Bprime_seed']}_it{row['Bprime_iteration']}",
                         arm, d, round(c_sum, 4), round(pB_sum, 4), int(c_sum > pB_sum),
                         round(c_sum - pB_sum, 4), round(spend(), 4)])
            fh.flush()
            if spend() > SPEND_CAP:
                print(f"!!! SPEND TRIPWIRE ${spend():.2f} — ABORT (checkpoint saved)"); fh.close(); sys.exit(2)
        n_done += 1
        if n_done % 10 == 0 or SMOKE:
            print(f"  [{n_done}/{len(pairs)-len(done)}] spend ${spend():.4f}", flush=True)
    fh.close()
    print(f"\nDONE {n_done} new batches. proposer ${refl.total_cost:.4f} + task ${adapter._lm.total_cost:.4f} "
          f"= ${spend():.4f} -> {CALLS}", flush=True)


if __name__ == "__main__":
    main()
