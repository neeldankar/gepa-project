"""Stage-1 Step B — one fresh HoVer baseline, seed 0, bigger trainset, full capture.

COPY of ../hover_probe/necrosis_run.py. Only three things changed vs the frozen reference run:
  (1) OUT -> absolute scratch/hover_stage1/stage1_seed0
  (2) trainset source -> scratch/hover_stage1/graded_records.jsonl imperfect claims (not
      eyeball_records.jsonl); each carries its threehop_idx, recorded for plan.md
  (3) N_TRAIN -> up to 100 (frozen was 12)
Everything else — model gpt-4.1-mini, BM25 retrieval, title-recall metric + build_si feedback,
max_metric_calls=300, N_VAL=10, reflection_minibatch_size=3, pareto/round_robin, num_threads=1,
use_merge=False, track_stats=True, seed=0, and ALL persistence dumps — is byte-identical to frozen.

  ../hover_probe/.venv/bin/python stage1_run.py --dry   # tiny instrumentation check (~$0.05)
  ../hover_probe/.venv/bin/python stage1_run.py         # seed-0 full run (mm=300, cap $5)
"""
from __future__ import annotations

import json
import os
import sys

import litellm
import orjson

HOVER_PROBE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hover_probe"))
STAGE1_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, HOVER_PROBE)
os.chdir(HOVER_PROBE)  # probe relative paths (bm25s_index/, threehop.jsonl, ../../.env)
import probe  # noqa: E402

DRY = "--dry" in sys.argv
SEED = int(sys.argv[sys.argv.index("--seed") + 1]) if "--seed" in sys.argv else 0
OUT = os.path.join(STAGE1_DIR, f"stage1_seed{SEED}_dry" if DRY else f"stage1_seed{SEED}")
# clobber guard: never overwrite a completed seed dir
if not DRY and os.path.exists(os.path.join(OUT, "run_summary.json")):
    raise SystemExit(f"REFUSE: {OUT}/run_summary.json exists — not clobbering seed {SEED}")
GRADED = os.path.join(STAGE1_DIR, "graded_records.jsonl")
MODEL = "openai/gpt-4.1-mini"
REFLECT_SIG = "I provided an assistant with the following instructions"
SPEND_CAP = 0.30 if DRY else 5.00
MM = 14 if DRY else 300
N_VAL = 4 if DRY else 10
N_TRAIN = 6 if DRY else 100     # frozen was 12; bigger trainset per Stage-1 brief
os.makedirs(OUT, exist_ok=True)

WIRE: list[str] = []
TRIPWIRE_USD = 4.50
_COST = {"usd": 0.0}
def _wire_cb(kwargs, completion_response, start_time, end_time):
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


def main():
    import dspy
    from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback

    probe._load_env()
    task_lm = dspy.LM(MODEL, max_tokens=3000, cache=False)
    dspy.configure(lm=task_lm)

    REFLECTIONS: list[dict] = []

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

    # ---------- imperfect claims from the freshly-graded threehop slice ----------
    recs = [orjson.loads(l) for l in open(GRADED, "rb")]
    imperfect = [r for r in recs if r["recall"] < 1.0]
    imperfect.sort(key=lambda r: (-r["recall"], r["claim"]))   # same key as frozen
    need = N_TRAIN + N_VAL
    if len(imperfect) < need:
        chosen = (imperfect * ((need // len(imperfect)) + 1))[:need]  # frozen cycling fallback
    else:
        chosen = imperfect[:need]
    examples = [dspy.Example(claim=r["claim"], titles=r["gold"]).with_inputs("claim") for r in chosen]
    trainset, valset = examples[:N_TRAIN], examples[N_TRAIN:need]
    train_ids = [r["threehop_idx"] for r in chosen[:N_TRAIN]]
    val_ids = [r["threehop_idx"] for r in chosen[N_TRAIN:need]]
    print(f"[{'DRY' if DRY else 'FULL'}] mm={MM} train={len(trainset)} val={len(valset)} "
          f"(imperfect pool={len(imperfect)}, cycled={len(imperfect) < need})")
    json.dump({"n_train": len(trainset), "n_val": len(valset), "train_threehop_ids": train_ids,
               "val_threehop_ids": val_ids, "imperfect_pool": len(imperfect),
               "cycled": len(imperfect) < need},
              open(f"{OUT}/trainset_manifest.json", "w"), indent=2)

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
        use_merge=False,
        log_dir=os.path.abspath(f"{OUT}/gepa_log"), seed=SEED,
    )
    print(f"=== dspy.GEPA compile (mm={MM}, cap ${SPEND_CAP}) ===")
    import time
    _t0 = time.time()
    gepa.compile(build_program(dspy), trainset=trainset, valset=valset)
    wall_s = time.time() - _t0
    retr_log.close()

    import pickle
    st = pickle.load(open(f"{OUT}/gepa_log/gepa_state.bin", "rb"))
    state_dump = {
        "prog_candidate_val_subscores": st["prog_candidate_val_subscores"],
        "parent_program_for_candidate": st["parent_program_for_candidate"],
        "num_metric_calls_by_discovery": st["num_metric_calls_by_discovery"],
        "program_candidates": st["program_candidates"],
        "list_of_named_predictors": st["list_of_named_predictors"],
        "full_program_trace": st["full_program_trace"],
        "n_val": len(valset),
        "trainset_claims": [ex.claim for ex in trainset],
        "trainset_threehop_ids": train_ids,
        "valset_threehop_ids": val_ids,
    }
    json.dump(state_dump, open(f"{OUT}/gepa_result.json", "w"), indent=2, ensure_ascii=False)
    json.dump(REFLECTIONS, open(f"{OUT}/reflections.json", "w"), ensure_ascii=False, indent=2)

    task_calls, refl_calls, actual = len(task_lm.history), len(reflection_lm.history), spend()
    tr = st["full_program_trace"]
    n_cand = len(st["program_candidates"])
    n_accept_inferred = sum(
        1 for e in tr
        if e.get("new_subsample_scores")   # some trace entries have no child subsample scores
        and (sum(e["new_subsample_scores"]) / len(e["new_subsample_scores"]))
         > (sum(e["subsample_scores"]) / len(e["subsample_scores"]))
    )
    print("\n===== STAGE1 SEED-0 RUN SUMMARY =====")
    print(f"reflection events captured: {len(REFLECTIONS)}  (wire seen: {len(WIRE)})  trace entries: {len(tr)}")
    print(f"accepted candidates (incl seed): {n_cand}  -> non-seed: {n_cand-1}  | accepts inferred: {n_accept_inferred}")
    print(f"event/trace 1:1 aligned: {len(REFLECTIONS) == len(tr)}   accept-inference matches: {n_accept_inferred == n_cand-1}")
    print(f"total LM calls: task={task_calls} reflection={refl_calls} (sum={task_calls+refl_calls})")
    print(f"actual spend: ${actual:.4f}  (cap ${SPEND_CAP})   wall_clock: {wall_s:.1f}s")
    json.dump({"seed": SEED, "reflection_events": len(REFLECTIONS), "trace_entries": len(tr),
               "candidates_incl_seed": n_cand, "accepts_inferred": n_accept_inferred,
               "event_trace_aligned": len(REFLECTIONS) == len(tr),
               "accept_inference_ok": n_accept_inferred == n_cand - 1,
               "task_calls": task_calls, "reflection_calls": refl_calls,
               "spend_usd": round(actual, 4), "wall_clock_s": round(wall_s, 1),
               "mm": MM, "n_train": len(trainset), "n_val": len(valset)},
              open(f"{OUT}/run_summary.json", "w"), indent=2)
    if actual > SPEND_CAP:
        print(f"WARNING: spend ${actual:.4f} exceeded cap ${SPEND_CAP}")


if __name__ == "__main__":
    main()
