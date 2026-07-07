"""HoVer GATE 1 — run a MINIMAL dspy.GEPA reflection step and CAPTURE, verbatim, exactly what
the reflection LM receives (belt-and-suspenders, ported from scripts/capture_reflection.py).

Two independent capture layers, cross-checked byte-for-byte:
  Layer A (wrapper): CaptureDSpyLM(dspy.LM).__call__ dumps the prompt string before forwarding.
  Layer B (wire):    litellm.success_callback captures kwargs["messages"] (LM -> API payload).
dspy.LM.forward builds messages=[{"role":"user","content":prompt}] (no system prepended), so
A == B is expected; if they diverge, the wire payload is ground truth (flagged).

We do NOT build scorers here. Purpose: confirm the reflection object is RICH (hop reasoning +
generated query + retrieved passage TEXT), not just the thin "docs remaining" annotation.

Run:  cd scratch/hover_probe && .venv/bin/python gepa_capture.py
"""
from __future__ import annotations

import json
import os
import sys

import litellm
import orjson

import probe  # reuse: search, title_of, build_si, load_index, NUM_DOCS, NUM_HOPS, _load_env, PRICE_*

OUT = "capture"
MODEL = "openai/gpt-4.1-mini"        # task == reflection; captured INPUT is model-independent
REFLECT_SIG = "I provided an assistant with the following instructions"
SPEND_CAP = 0.50
MAX_METRIC_CALLS = 24                 # ~2-3 proposals -> round_robin hits BOTH predictors
os.makedirs(OUT, exist_ok=True)

# ---------- Layer B: independent wire capture (scan ALL messages for the reflection prompt) ----------
WIRE: list[str] = []
def _wire_cb(kwargs, completion_response, start_time, end_time):
    for m in (kwargs.get("messages") or []):
        c = m.get("content")
        if isinstance(c, str) and c.startswith(REFLECT_SIG):
            WIRE.append(c)
            break
litellm.success_callback = [_wire_cb]


def build_program(dspy):
    class HoverMultiHop(dspy.Module):
        def __init__(self):
            super().__init__()
            self.gen_query = dspy.ChainOfThought("claim, notes -> query")
            self.append_notes = dspy.ChainOfThought(
                "claim, notes, context -> new_notes: list[str], titles: list[str]")

        def forward(self, claim):
            notes, per_hop = [], []
            for hop in range(probe.NUM_HOPS):
                q = self.gen_query(claim=claim, notes=notes).query
                ctx = probe.search(q, k=probe.NUM_DOCS)
                ret_titles = [probe.title_of(c) for c in ctx]
                per_hop.append({"hop": hop + 1, "query": q, "retrieved_titles": ret_titles})
                pred = self.append_notes(claim=claim, notes=notes, context=ctx)
                new = pred.new_notes if isinstance(pred.new_notes, list) else [str(pred.new_notes)]
                notes.extend(new)
            all_ret = sorted({t for h in per_hop for t in h["retrieved_titles"]})
            return dspy.Prediction(titles=all_ret, notes=notes, per_hop=per_hop)

    return HoverMultiHop()


def main():
    import dspy
    from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback

    probe._load_env()
    task_lm = dspy.LM(MODEL, max_tokens=3000, cache=False)
    dspy.configure(lm=task_lm)

    # ---------- Layer A: wrapper on the reflection LM instance ----------
    class CaptureDSpyLM(dspy.LM):
        A_PROMPTS: list[str] = []

        def __call__(self, prompt=None, messages=None, **kwargs):
            if isinstance(prompt, str) and prompt.startswith(REFLECT_SIG):
                i = len(CaptureDSpyLM.A_PROMPTS) + 1
                CaptureDSpyLM.A_PROMPTS.append(prompt)
                with open(f"{OUT}/reflect_{i}.txt", "w", encoding="utf-8") as f:
                    f.write(prompt)
                with open(f"{OUT}/reflect_{i}.json", "w", encoding="utf-8") as f:
                    json.dump([{"role": "user", "content": prompt}], f, ensure_ascii=False, indent=2)
                with open(f"{OUT}/reflect_{i}.repr", "w", encoding="utf-8") as f:
                    f.write(repr(prompt))
            return super().__call__(prompt=prompt, messages=messages, **kwargs)

    reflection_lm = CaptureDSpyLM(MODEL, temperature=1.0, max_tokens=4000, cache=False)

    # ---------- metric: recall score + build_si feedback (rich channel comes from the TRACE) ----------
    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        g = set(getattr(gold, "titles", []) or [])
        got = set(getattr(pred, "titles", []) or [])
        recall = (len(g & got) / len(g)) if g else 0.0
        fb = probe.build_si(list(g), list(got))
        return ScoreWithFeedback(score=recall, feedback=fb)

    # ---------- imperfect-recall claims (so skip_perfect_score doesn't suppress reflection) ----------
    recs = [orjson.loads(l) for l in open("eyeball_records.jsonl")]
    imperfect = [r for r in recs if r["recall"] < 1.0]
    # spread of difficulty: interleave 0.67 near-miss / 0.33 / 0.0
    imperfect.sort(key=lambda r: (-r["recall"], r["claim"]))
    chosen = imperfect[:6] + imperfect[-3:]          # 6 near/mid + 3 hardest = 9 claims
    examples = [dspy.Example(claim=r["claim"], titles=r["gold"]).with_inputs("claim") for r in chosen]
    trainset, valset = examples[:6], examples[6:]
    print(f"claims: {len(examples)} imperfect (train {len(trainset)} / val {len(valset)}); "
          f"recalls={[round(r['recall'],2) for r in chosen]}")

    def spend():
        tot = 0.0
        for lm in (task_lm, reflection_lm):
            for h in lm.history:
                u = h.get("usage") or {}
                tot += (u.get("prompt_tokens", 0) * probe.PRICE_IN
                        + u.get("completion_tokens", 0) * probe.PRICE_OUT)
        return tot

    gepa = dspy.GEPA(
        metric=metric,
        reflection_lm=reflection_lm,
        max_metric_calls=MAX_METRIC_CALLS,
        reflection_minibatch_size=3,
        candidate_selection_strategy="pareto",
        component_selector="round_robin",
        num_threads=1,
        track_stats=True,
        seed=0,
    )
    print(f"=== running dspy.GEPA (max_metric_calls={MAX_METRIC_CALLS}, cap ${SPEND_CAP}) ===")
    gepa.compile(build_program(dspy), trainset=trainset, valset=valset)

    # ---------- cross-check A == B ----------
    A = CaptureDSpyLM.A_PROMPTS
    task_calls = len(task_lm.history)
    refl_calls = len(reflection_lm.history)
    actual = spend()
    print("\n===== CAPTURE SUMMARY =====")
    print(f"reflection calls (Layer A): {len(A)}   wire reflection msgs (Layer B): {len(WIRE)}")
    print(f"total LM calls: task={task_calls}  reflection={refl_calls}  (sum={task_calls+refl_calls})")
    print(f"actual spend: ${actual:.4f}  (cap ${SPEND_CAP})")
    n = min(len(A), len(WIRE))
    all_eq = True
    for i in range(n):
        eq = (A[i] == WIRE[i])
        all_eq &= eq
        print(f"  call {i+1}: A==B(wire) {eq} | len={len(A[i])}")
    verdict = "PASS" if (all_eq and n > 0) else ("FAIL/DIVERGENCE" if n > 0 else "NO REFLECTION CALLS")
    print(f"BYTE EQUALITY A==B over {n} calls: {verdict}")
    json.dump({"reflection_calls": len(A), "wire_calls": len(WIRE),
               "task_calls": task_calls, "reflection_lm_calls": refl_calls,
               "byte_equal_A_B": bool(all_eq and n > 0), "spend_usd": round(actual, 4),
               "max_metric_calls": MAX_METRIC_CALLS},
              open(f"{OUT}/equality.json", "w"), indent=2)
    if actual > SPEND_CAP:
        print(f"WARNING: spend ${actual:.4f} exceeded cap ${SPEND_CAP}")


if __name__ == "__main__":
    main()
