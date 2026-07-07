"""HoVer necrosis kill-switch — Step 0 (dry) + Step 1 (lean mm~300) run + full capture.

Extends the GATE 1 capture harness (leaves gepa_capture.py intact). Per reflection call captures
BOTH the input prompt (the rich object) and the raw OUTPUT instruction (the join key to the
accepted candidate). Dumps dspy.GEPA detailed_results (val_subscores/parents/discovery order +
per-candidate per-component instructions) so per-event ΔU can be reconstructed OFFLINE (main .venv).

  .venv/bin/python necrosis_run.py --dry     # Step 0: tiny mm~8, ~$0.05, validate instrumentation
  .venv/bin/python necrosis_run.py           # Step 1: mm~300, valset~10, ~$2-3, hard cap $5
"""
from __future__ import annotations

import json
import os
import sys

import litellm
import orjson

import probe

DRY = "--dry" in sys.argv
OUT = "necrosis_dry" if DRY else "necrosis"
MODEL = "openai/gpt-4.1-mini"
REFLECT_SIG = "I provided an assistant with the following instructions"
SPEND_CAP = 0.30 if DRY else 5.00
MM = 14 if DRY else 300
N_VAL = 4 if DRY else 10
N_TRAIN = 6 if DRY else 12
os.makedirs(OUT, exist_ok=True)

WIRE: list[str] = []
TRIPWIRE_USD = 4.50          # hard-cap tripwire (best-effort mid-run kill; mm is the structural ceiling)
_COST = {"usd": 0.0}
def _wire_cb(kwargs, completion_response, start_time, end_time):
    # accumulate est spend and trip the hard cap
    try:
        u = getattr(completion_response, "usage", None) or {}
        pin = u.get("prompt_tokens", 0) if isinstance(u, dict) else getattr(u, "prompt_tokens", 0)
        pout = u.get("completion_tokens", 0) if isinstance(u, dict) else getattr(u, "completion_tokens", 0)
        _COST["usd"] += pin * probe.PRICE_IN + pout * probe.PRICE_OUT
    except Exception:
        pass
    if _COST["usd"] > TRIPWIRE_USD:
        raise RuntimeError(f"SPEND TRIPWIRE: est ${_COST['usd']:.3f} > ${TRIPWIRE_USD} — aborting run")
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


def predictor_instructions(module) -> dict:
    """{component_name: instruction text} for a candidate dspy Module."""
    out = {}
    for name, pred in module.named_predictors():
        sig = getattr(pred, "signature", None)
        out[name] = getattr(sig, "instructions", "") if sig is not None else ""
    return out


def main():
    import dspy
    from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback

    probe._load_env()
    task_lm = dspy.LM(MODEL, max_tokens=3000, cache=False)
    dspy.configure(lm=task_lm)

    # ---------- Layer A: capture reflection INPUT + OUTPUT per call ----------
    REFLECTIONS: list[dict] = []   # {idx, prompt, output}

    class CaptureDSpyLM(dspy.LM):
        def __call__(self, prompt=None, messages=None, **kwargs):
            is_reflect = isinstance(prompt, str) and prompt.startswith(REFLECT_SIG)
            out = super().__call__(prompt=prompt, messages=messages, **kwargs)
            if is_reflect:
                idx = len(REFLECTIONS) + 1
                raw = out[0] if isinstance(out, list) and out else out
                raw = raw.get("text") if isinstance(raw, dict) else raw
                REFLECTIONS.append({"idx": idx, "prompt": prompt, "output": str(raw)})
                with open(f"{OUT}/reflect_in_{idx}.txt", "w", encoding="utf-8") as f:
                    f.write(prompt)
                with open(f"{OUT}/reflect_out_{idx}.txt", "w", encoding="utf-8") as f:
                    f.write(str(raw))
            return out

    reflection_lm = CaptureDSpyLM(MODEL, temperature=1.0, max_tokens=4000, cache=False)

    # ---------- metric: recall + build_si feedback; side-log retrieval controls ----------
    retr_log = open(f"{OUT}/retrieval_log.jsonl", "wb")

    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        g = set(getattr(gold, "titles", []) or [])
        got = set(getattr(pred, "titles", []) or [])
        recall = (len(g & got) / len(g)) if g else 0.0
        fb = probe.build_si(list(g), list(got))
        retr_log.write(orjson.dumps({
            "claim": getattr(gold, "claim", ""), "gold": sorted(g), "retrieved": sorted(got),
            "recall": recall, "n_retrieved": len(got), "overlap": len(g & got),
            "per_hop": getattr(pred, "per_hop", []),
        }) + b"\n")
        return ScoreWithFeedback(score=recall, feedback=fb)

    # ---------- imperfect claims ----------
    recs = [orjson.loads(l) for l in open("eyeball_records.jsonl")]
    imperfect = [r for r in recs if r["recall"] < 1.0]
    imperfect.sort(key=lambda r: (-r["recall"], r["claim"]))
    need = N_TRAIN + N_VAL
    chosen = (imperfect * ((need // len(imperfect)) + 1))[:need]
    examples = [dspy.Example(claim=r["claim"], titles=r["gold"]).with_inputs("claim") for r in chosen]
    trainset, valset = examples[:N_TRAIN], examples[N_TRAIN:need]
    print(f"[{'DRY' if DRY else 'FULL'}] mm={MM} train={len(trainset)} val={len(valset)}")

    def spend():
        tot = 0.0
        for lm in (task_lm, reflection_lm):
            for h in lm.history:
                u = h.get("usage") or {}
                tot += (u.get("prompt_tokens", 0) * probe.PRICE_IN
                        + u.get("completion_tokens", 0) * probe.PRICE_OUT)
        return tot

    gepa = dspy.GEPA(
        metric=metric, reflection_lm=reflection_lm, max_metric_calls=MM,
        reflection_minibatch_size=3, candidate_selection_strategy="pareto",
        component_selector="round_robin", num_threads=1, track_stats=True,
        use_merge=False,   # every trace entry == exactly one reflection call (clean 1:1 join)
        log_dir=os.path.abspath(f"{OUT}/gepa_log"), seed=0,
    )
    print(f"=== dspy.GEPA compile (mm={MM}, cap ${SPEND_CAP}) ===")
    gepa.compile(build_program(dspy), trainset=trainset, valset=valset)
    retr_log.close()

    # ---------- dump the gepa STATE (pure builtins, JSON-serializable) for offline ΔU ----------
    import pickle
    st = pickle.load(open(f"{OUT}/gepa_log/gepa_state.bin", "rb"))
    state_dump = {
        # per-candidate per-instance valset scores: list[dict{instance_id: score}]  (accepted only)
        "prog_candidate_val_subscores": st["prog_candidate_val_subscores"],
        "parent_program_for_candidate": st["parent_program_for_candidate"],
        "num_metric_calls_by_discovery": st["num_metric_calls_by_discovery"],
        "program_candidates": st["program_candidates"],            # list[dict{component: instruction}]
        "list_of_named_predictors": st["list_of_named_predictors"],
        # per-iteration: i, selected_program_candidate(parent), subsample_ids(minibatch trainset idx),
        # subsample_scores(parent), new_subsample_scores(child) -> accept = mean(new)>mean(old)
        "full_program_trace": st["full_program_trace"],
        "n_val": len(valset),
        "trainset_claims": [ex.claim for ex in trainset],           # subsample_ids index into this
    }
    json.dump(state_dump, open(f"{OUT}/gepa_result.json", "w"), indent=2, ensure_ascii=False)
    json.dump(REFLECTIONS, open(f"{OUT}/reflections.json", "w"), ensure_ascii=False, indent=2)

    task_calls, refl_calls, actual = len(task_lm.history), len(reflection_lm.history), spend()
    tr = st["full_program_trace"]
    n_cand = len(st["program_candidates"])
    n_accept_inferred = sum(
        1 for e in tr
        if (sum(e["new_subsample_scores"]) / len(e["new_subsample_scores"]))
         > (sum(e["subsample_scores"]) / len(e["subsample_scores"]))
    )
    print("\n===== NECROSIS RUN SUMMARY =====")
    print(f"reflection events captured: {len(REFLECTIONS)}  (wire seen: {len(WIRE)})  trace entries: {len(tr)}")
    print(f"accepted candidates (incl seed): {n_cand}  -> non-seed: {n_cand-1}  | accepts inferred from trace: {n_accept_inferred}")
    print(f"event/trace 1:1 aligned: {len(REFLECTIONS) == len(tr)}   accept-inference matches: {n_accept_inferred == n_cand-1}")
    print(f"total LM calls: task={task_calls} reflection={refl_calls} (sum={task_calls+refl_calls})")
    print(f"actual spend: ${actual:.4f}  (cap ${SPEND_CAP})")
    json.dump({"reflection_events": len(REFLECTIONS), "trace_entries": len(tr),
               "candidates_incl_seed": n_cand, "accepts_inferred": n_accept_inferred,
               "event_trace_aligned": len(REFLECTIONS) == len(tr),
               "accept_inference_ok": n_accept_inferred == n_cand - 1,
               "task_calls": task_calls, "reflection_calls": refl_calls,
               "spend_usd": round(actual, 4), "mm": MM},
              open(f"{OUT}/run_summary.json", "w"), indent=2)
    if actual > SPEND_CAP:
        print(f"WARNING: spend ${actual:.4f} exceeded cap ${SPEND_CAP}")


if __name__ == "__main__":
    main()
