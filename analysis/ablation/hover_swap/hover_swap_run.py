"""Stage-2 Phase 1 — HoVer batch-swap smoke (5 pairs). Ports batch_swap_v2_run.py to the frozen
Stage-1 HoVer corpus using the SAME dspy code path that produced it (DspyAdapter + HoverMultiHop +
gepa InstructionProposalSignature), so SAME/SWAP reflection inputs match the frozen format by
construction. Real parent execution on B_e only — no synthesized feedback.

Per pair (event e): reconstruct Φ_e + reflected component; A_e=subsample_ids (logged parent scores);
draw M=6 (census RNG), run Φ_e on 6 (capture_traces) -> pick 3 best parent-score-multiset match = B_e
(those runs also supply the SWAP reflection object + B_e baseline); SAME input from a fresh Φ_e run on
A_e. Byte-verify both reflect inputs. K=3 child draws/arm; each child evaluated on BOTH A_e and B_e;
per-draw per-example vectors + full child text persisted.

  python3 analysis/ablation/hover_swap/hover_swap_run.py --validate   # $0, no API: scaffolding checks
  python3 analysis/ablation/hover_swap/hover_swap_run.py              # live 5-pair smoke (cap ~$5)
"""
from __future__ import annotations
import json, os, sys, time, random, hashlib
import litellm, orjson

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HOVER_PROBE = os.path.join(REPO, "scratch", "hover_probe")
S1 = os.path.join(REPO, "scratch", "hover_stage1")
OUT = os.path.join(REPO, "analysis", "ablation", "hover_swap")
sys.path.insert(0, HOVER_PROBE)
os.chdir(HOVER_PROBE)  # probe relative paths (bm25s_index/, threehop.jsonl, ../../.env)
import probe  # noqa: E402

VALIDATE = "--validate" in sys.argv
MODEL = "openai/gpt-4.1-mini"
K = 3
M = 6
NUM_THREADS = 4   # eval parallelism only (per-example independent -> results identical to 1 thread)
SPEND_CAP = 5.00
TRIPWIRE = 4.50
# 5 smoke pairs: span both components (even ordinal->gen_query, odd->append_notes via round-robin),
# non-seed parents (later events), and a recovered seed (6). (seed, event_ordinal 0-indexed)
SMOKE_PAIRS = [(0, 0), (0, 1), (6, 4), (4, 7), (2, 10)]

REFLECT_SIG = "I provided an assistant with the following instructions"
_COST = {"usd": 0.0}
def _wire_cb(kwargs, completion_response, start_time, end_time):
    try:
        u = getattr(completion_response, "usage", None) or {}
        pin = u.get("prompt_tokens", 0) if isinstance(u, dict) else getattr(u, "prompt_tokens", 0)
        pout = u.get("completion_tokens", 0) if isinstance(u, dict) else getattr(u, "completion_tokens", 0)
        _COST["usd"] += pin * probe.PRICE_IN + pout * probe.PRICE_OUT
    except Exception:
        pass
    if _COST["usd"] > TRIPWIRE:
        raise RuntimeError(f"SPEND TRIPWIRE ${_COST['usd']:.3f} > ${TRIPWIRE}")
litellm.success_callback = [_wire_cb]

def seed_of(*parts):
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return int(h[:8], 16)

def build_student(dspy):
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
                rt = [probe.title_of(c) for c in ctx]
                per_hop.append({"hop": hop + 1, "query": q, "retrieved_titles": rt})
                pred = self.append_notes(claim=claim, notes=notes, context=ctx)
                new = pred.new_notes if isinstance(pred.new_notes, list) else [str(pred.new_notes)]
                notes.extend(new)
            all_ret = sorted({t for h in per_hop for t in h["retrieved_titles"]})
            return dspy.Prediction(titles=all_ret, notes=notes, per_hop=per_hop)
    return HoverMultiHop()

def make_metric(dspy):
    from dspy.teleprompt.gepa.gepa_utils import ScoreWithFeedback
    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        g = set(getattr(gold, "titles", []) or [])
        got = set(getattr(pred, "titles", []) or [])
        recall = (len(g & got) / len(g)) if g else 0.0
        return ScoreWithFeedback(score=recall, feedback=probe.build_si(list(g), list(got)))
    return metric

def load_seed(seed):
    d = os.path.join(S1, f"stage1_seed{seed}")
    gr = json.load(open(os.path.join(d, "gepa_result.json")))
    tm = json.load(open(os.path.join(d, "trainset_manifest.json")))
    graded = {r["threehop_idx"]: r for r in (orjson.loads(l) for l in open(os.path.join(S1, "graded_records.jsonl"), "rb"))}
    train = [graded[tid] for tid in tm["train_threehop_ids"]]  # position -> record
    events = [e for e in gr["full_program_trace"] if e.get("new_subsample_scores")]
    return d, gr, tm, train, events

def reflect_in_instr(seed_dir, event_ordinal):
    """current_instruction_doc extracted from the frozen reflect_in for this event (1-indexed file)."""
    from gepa.strategies.instruction_proposal import InstructionProposalSignature as IPS
    T = IPS.default_prompt_template
    pre, rest = T.split("<curr_instructions>"); mid, _ = rest.split("<inputs_outputs_feedback>")
    txt = open(os.path.join(seed_dir, f"reflect_in_{event_ordinal+1}.txt"), encoding="utf-8").read()
    inner = txt[len(pre):]
    return inner.split(mid, 1)[0]

def byte_verify(reflect_in_text):
    from gepa.strategies.instruction_proposal import InstructionProposalSignature as IPS
    T = IPS.default_prompt_template
    pre, rest = T.split("<curr_instructions>"); mid, post = rest.split("<inputs_outputs_feedback>")
    if not (reflect_in_text.startswith(pre) and reflect_in_text.endswith(post) and mid in reflect_in_text):
        return False
    inner = reflect_in_text[len(pre):len(reflect_in_text)-len(post)]
    INSTR, BODY = inner.split(mid, 1)
    recon = T.replace("<curr_instructions>", INSTR).replace("<inputs_outputs_feedback>", BODY)
    return recon == reflect_in_text and BODY.startswith("# Example 1") \
        and all(k in BODY for k in ["## Inputs", "## Generated Outputs", "## Feedback"])

def multiset_match(target_scores, cand_scores_list):
    """Pick 3 indices whose parent-score multiset best matches target (exact preferred, min-L1)."""
    from itertools import combinations
    tgt = sorted(target_scores)
    best = None
    for combo in combinations(range(len(cand_scores_list)), 3):
        ms = sorted(cand_scores_list[i] for i in combo)
        l1 = sum(abs(a - b) for a, b in zip(ms, tgt))
        exact = (ms == tgt)
        key = (0 if exact else 1, l1)
        if best is None or key < best[0]:
            best = (key, combo, l1, exact)
    return best[1], best[2], best[3]  # combo, l1, exact

def sub_batch(eb, idxs, EvaluationBatch):
    trajs = [eb.trajectories[i] for i in idxs] if eb.trajectories else None
    return EvaluationBatch(outputs=[eb.outputs[i] for i in idxs],
                           scores=[eb.scores[i] for i in idxs], trajectories=trajs)

def main():
    import dspy
    from dspy.teleprompt.gepa.gepa_utils import DspyAdapter, EvaluationBatch
    from gepa.strategies.instruction_proposal import InstructionProposalSignature as IPS
    probe._load_env()

    plan = {(r["seed"], r["trace_i"]): r for r in (json.loads(l) for l in open(os.path.join(OUT, "pairing_plan.jsonl")))}
    student = build_student(dspy)
    metric = make_metric(dspy)
    prednames = [n for n, _ in student.named_predictors()]

    task_lm = dspy.LM(MODEL, max_tokens=3000, cache=False)
    reflection_lm = dspy.LM(MODEL, temperature=1.0, max_tokens=4000, cache=False)
    dspy.configure(lm=task_lm)

    rows_path = os.path.join(OUT, "smoke_draws.jsonl")
    inputs_dir = os.path.join(OUT, "smoke_reflect_inputs"); os.makedirs(inputs_dir, exist_ok=True)
    rows = open(rows_path, "w") if not VALIDATE else None
    pair_meta = []

    for pi, (seed, ordinal) in enumerate(SMOKE_PAIRS):
        d, gr, tm, train, events = load_seed(seed)
        ev = events[ordinal]; trace_i = ev["i"]
        pr = plan[(seed, trace_i)]
        parent_cand = gr["program_candidates"][ev["selected_program_candidate"]]
        # component = the one whose instruction equals the frozen reflect_in's current_instruction_doc
        finstr = reflect_in_instr(d, ordinal)
        comp = next((n for n in prednames if parent_cand.get(n) == finstr), None)
        A_pos = pr["A_e_pos"]; A_par_logged = pr["A_e_parent_scores"]; draw6 = pr["draw6_pos"]
        def ex(pos): return dspy.Example(claim=train[pos]["claim"], titles=train[pos]["gold"]).with_inputs("claim")
        A_e = [ex(p) for p in A_pos]
        cand6 = [ex(p) for p in draw6]
        meta = {"pair": pi, "seed": seed, "trace_i": trace_i, "event_ordinal": ordinal, "comp": comp,
                "parent_candidate_idx": ev["selected_program_candidate"],
                "A_e_pos": A_pos, "A_e_parent_scores_logged": A_par_logged, "draw6_pos": draw6,
                "component_matched": comp is not None}
        if VALIDATE:
            meta["comps_available"] = prednames
            meta["instr_len"] = len(finstr)
            pair_meta.append(meta)
            print(f"pair {pi} seed{seed} ev{ordinal} trace_i={trace_i}: comp={comp} "
                  f"matched={comp is not None} |A_e|={len(A_e)} |cand6|={len(cand6)} "
                  f"parent_idx={ev['selected_program_candidate']}")
            continue

        if comp is None:
            raise SystemExit(f"pair {pi}: component match FAILED (seed{seed} ev{ordinal}) — do not approximate")

        t0 = time.time()
        adapter = DspyAdapter(student_module=student, metric_fn=metric,
                              feedback_map={k: _fbmap(metric, k, p) for k, p in student.named_predictors()},
                              failure_score=0.0, num_threads=NUM_THREADS, add_format_failure_as_feedback=False,
                              rng=random.Random(seed_of(seed, trace_i)), reflection_lm=reflection_lm,
                              reflection_minibatch_size=3)
        # failure-match: run parent on the 6 candidates (capture traces -> also the SWAP reflection obj)
        eb6 = adapter.evaluate(cand6, parent_cand, capture_traces=True)
        combo, l1, exact = multiset_match(A_par_logged, list(eb6.scores))
        B_idx = list(combo); B_pos = [draw6[i] for i in B_idx]
        B_par_fresh = [eb6.scores[i] for i in B_idx]
        ebB = sub_batch(eb6, B_idx, EvaluationBatch)
        B_e = [cand6[i] for i in B_idx]
        # SAME reflection object: fresh parent run on A_e (logged traces are gone)
        ebA = adapter.evaluate(A_e, parent_cand, capture_traces=True)

        arms = {"SAME": ebA, "SWAP": ebB}
        for arm, eb in arms.items():
            adapter.rng = random.Random(seed_of(seed, trace_i, arm))
            rd = adapter.make_reflective_dataset(parent_cand, eb, [comp])
            reflect_in = IPS.prompt_renderer({"current_instruction_doc": parent_cand[comp],
                                              "dataset_with_feedback": rd[comp]})
            if not byte_verify(reflect_in):
                raise SystemExit(f"pair {pi} {arm}: reflect_in byte-verify FAILED — stop, do not approximate")
            open(os.path.join(inputs_dir, f"pair{pi}_{arm}_reflect_in.txt"), "w", encoding="utf-8").write(reflect_in)
            for draw in range(K):
                ds = seed_of(seed, trace_i, arm, draw)
                raw = reflection_lm(reflect_in)
                text = raw[0] if isinstance(raw, list) else raw
                text = text.get("text") if isinstance(text, dict) else text
                child_instr = IPS.output_extractor(str(text))["new_instruction"]
                child_cand = {**parent_cand, comp: child_instr}
                scoresA = adapter.evaluate(A_e, child_cand, capture_traces=False).scores
                scoresB = adapter.evaluate(B_e, child_cand, capture_traces=False).scores
                rows.write(json.dumps({
                    "pair": pi, "seed": seed, "trace_i": trace_i, "comp": comp, "arm": arm, "draw": draw,
                    "draw_seed": ds, "child_instruction": child_instr,
                    "scores_on_A_e": [float(x) for x in scoresA],
                    "scores_on_B_e": [float(x) for x in scoresB],
                    "A_e_pos": A_pos, "B_e_pos": B_pos,
                    "A_e_parent_scores_logged": A_par_logged, "B_e_parent_scores_fresh": [float(x) for x in B_par_fresh],
                    "match_exact": exact, "match_l1": l1,
                }) + "\n"); rows.flush()
        dt = time.time() - t0
        meta.update({"B_e_pos": B_pos, "B_e_parent_scores_fresh": [float(x) for x in B_par_fresh],
                     "match_exact": exact, "match_l1": l1, "pair_wall_s": round(dt, 1),
                     "cum_spend_usd": round(_COST["usd"], 4)})
        pair_meta.append(meta)
        print(f"pair {pi} done: comp={comp} match_exact={exact} l1={l1} {dt:.1f}s cum=${_COST['usd']:.4f}")

    if VALIDATE:
        json.dump(pair_meta, open(os.path.join(OUT, "smoke_validate.json"), "w"), indent=2)
        print("\nVALIDATE: all component matches:", all(m["component_matched"] for m in pair_meta))
        return
    rows.close()
    json.dump(pair_meta, open(os.path.join(OUT, "smoke_pairs_meta.json"), "w"), indent=2)
    print(f"\nSMOKE DONE: {len(SMOKE_PAIRS)} pairs, total ${_COST['usd']:.4f}")

# feedback_map factory replicating dspy.GEPA.feedback_fn_creator
def _fbmap(metric_fn, pred_name, predictor):
    def feedback_fn(predictor_output, predictor_inputs, module_inputs, module_outputs, captured_trace):
        o = metric_fn(module_inputs, module_outputs, captured_trace, pred_name, [(predictor, predictor_inputs, predictor_output)])
        if hasattr(o, "feedback"):
            if o["feedback"] is None:
                o["feedback"] = f"This trajectory got a score of {o['score']}."
            return o
        return dict(score=o, feedback=f"This trajectory got a score of {o}.")
    return feedback_fn

if __name__ == "__main__":
    main()
