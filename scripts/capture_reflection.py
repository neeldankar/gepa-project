"""EXACT capture of the reflection-LM input on the IFBench program (belt-and-suspenders).

Minimal IFBench GEPA run (tiny split, cheapest model) whose ONLY purpose is to dump, verbatim, the
literal object the reflection LM receives at call time — via TWO independent layers:
  Layer A (wrapper): CaptureLM(LM).__call__ dumps `prompt` before forwarding (the proposer->LM input).
  Layer B (wire):    litellm.success_callback captures kwargs["messages"] (the LM->API payload).
Then cross-checks both against the SAME run's logged `proposal_end.prompts.system_prompt`.

Run (pennies): .venv/bin/python scripts/capture_reflection.py
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

from dotenv import load_dotenv

load_dotenv()
if not os.environ.get("OPENAI_API_KEY", "").strip():
    sys.exit("ERROR: OPENAI_API_KEY not set.")

import litellm  # noqa: E402
from gepa import optimize  # noqa: E402
from gepa.adapters.default_adapter.default_adapter import DefaultAdapter  # noqa: E402
from gepa.lm import LM  # noqa: E402

from gepa_si.ifbench_eval import IFConstraintEvaluator  # noqa: E402
from gepa_si.ifrlvr_data import load_faithful_splits  # noqa: E402
from gepa_si.si_event_logger import SIEventLogger  # noqa: E402

OUT = "analysis/reflection_capture"
MODEL = "openai/gpt-4.1-mini"            # task == reflection; cheapest, output quality irrelevant
REFLECT_SIG = "I provided an assistant with the following instructions"
SEED_CANDIDATE = {"system_prompt": (
    "You are a helpful assistant. Read the user's request carefully and follow "
    "every instruction and formatting constraint exactly.")}

os.makedirs(OUT, exist_ok=True)

# ---------- Layer B: independent wire capture ----------
WIRE: list[str] = []
def _wire_cb(kwargs, completion_response, start_time, end_time):
    msgs = kwargs.get("messages") or []
    if msgs and isinstance(msgs[0].get("content"), str) and msgs[0]["content"].startswith(REFLECT_SIG):
        WIRE.append(msgs[0]["content"])
litellm.success_callback = [_wire_cb]


# ---------- Layer A: wrapper capture ----------
class CaptureLM(LM):
    A_PROMPTS: list[Any] = []     # exact objects received by the reflection LM

    def __call__(self, prompt: str | list[dict[str, Any]]) -> str:
        i = len(CaptureLM.A_PROMPTS) + 1
        CaptureLM.A_PROMPTS.append(prompt)
        # 1) raw .txt — content exactly as received
        if isinstance(prompt, str):
            raw = prompt
            messages = [{"role": "user", "content": prompt}]   # what LM.__call__ will send (lm.py:100)
        else:
            messages = prompt
            raw = "\n\n".join(f"<<{m.get('role')}>>\n{m.get('content')}" for m in prompt)
        with open(f"{OUT}/reflect_{i}.txt", "w", encoding="utf-8") as f:
            f.write(raw)
        with open(f"{OUT}/reflect_{i}.json", "w", encoding="utf-8") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
        with open(f"{OUT}/reflect_{i}.repr", "w", encoding="utf-8") as f:
            f.write(repr(prompt))
        return super().__call__(prompt)


def main():
    trainset, valset = load_faithful_splits()
    trainset, valset = trainset[:6], valset[:6]
    log_path = f"{OUT}/capture.jsonl"
    if os.path.exists(log_path):
        os.remove(log_path)

    adapter = DefaultAdapter(model=MODEL, evaluator=IFConstraintEvaluator())
    reflection_lm = CaptureLM(MODEL)
    logger = SIEventLogger(log_path, run_id="capture")
    try:
        optimize(seed_candidate=SEED_CANDIDATE, trainset=trainset, valset=valset, adapter=adapter,
                 reflection_lm=reflection_lm, reflection_minibatch_size=3,
                 max_metric_calls=40, seed=0, display_progress_bar=False, callbacks=[logger])
    finally:
        logger.close()

    # ---------- cross-check: A == B == logged proposal_end.prompts.system_prompt ----------
    logged = []
    for line in open(log_path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("event") == "proposal_end":
            logged.append((r.get("prompts") or {}).get("system_prompt"))

    A = [p if isinstance(p, str) else None for p in CaptureLM.A_PROMPTS]
    print(f"\n===== CAPTURE SUMMARY =====")
    print(f"task cost ${getattr(adapter._lm,'total_cost',0):.4f} + reflection ${reflection_lm.total_cost:.4f} "
          f"= ${getattr(adapter._lm,'total_cost',0)+reflection_lm.total_cost:.4f}")
    print(f"reflection calls (Layer A): {len(A)}   wire calls (Layer B): {len(WIRE)}   "
          f"logged proposal_end: {len(logged)}")
    n = min(len(A), len(WIRE), len(logged))
    all_eq = True
    for i in range(n):
        a_eq_b = (A[i] == WIRE[i])
        a_eq_log = (A[i] == logged[i])
        all_eq &= (a_eq_b and a_eq_log)
        print(f"  call {i+1}: A==B(wire) {a_eq_b} | A==logged {a_eq_log} | len(A)={len(A[i]) if A[i] else None}")
    print(f"THREE-WAY BYTE EQUALITY (A==B==logged) over {n} calls: {'PASS' if (all_eq and n>0) else 'FAIL/DIVERGENCE'}")
    json.dump({"reflection_calls": len(A), "wire_calls": len(WIRE), "logged": len(logged),
               "three_way_equal": bool(all_eq and n > 0),
               "task_usd": getattr(adapter._lm, "total_cost", 0), "reflect_usd": reflection_lm.total_cost},
              open(f"{OUT}/equality.json", "w"), indent=2)


if __name__ == "__main__":
    main()
