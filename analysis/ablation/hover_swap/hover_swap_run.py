"""Stage-2 HoVer batch-swap runner. Ports batch_swap_v2_run.py to the frozen Stage-1 HoVer corpus
using the SAME dspy path that produced it (DspyAdapter + HoverMultiHop + gepa InstructionProposalSignature),
so SAME/SWAP reflection inputs match the frozen format by construction. Real parent execution on B_e
only — no synthesized feedback.

Modes:
  --validate            $0, no API: parent reconstruction + component match for the 5 smoke pairs
  --pair SEED TRACE_I   run ONE pair -> pairs/seed<S>_i<TRACE_I>/{draws.jsonl,reflect_in_*,meta.json}
  (no args)             legacy 5-pair smoke (Phase 1) -> smoke_draws.jsonl
"""
from __future__ import annotations
import json, os, sys, time, random, hashlib
import litellm, orjson

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
HOVER_PROBE = os.path.join(REPO, "scratch", "hover_probe")
S1 = os.path.join(REPO, "scratch", "hover_stage1")
OUT = os.path.join(REPO, "analysis", "ablation", "hover_swap")
sys.path.insert(0, HOVER_PROBE)
os.chdir(HOVER_PROBE)
import probe  # noqa: E402
import bm25s  # noqa: E402

# --- memory-mapped BM25 index -------------------------------------------------
# probe.py is frozen (it produced the Stage-1 corpus and must stay byte-identical), so the
# mmap switch is monkeypatched here instead of edited there. probe.search() resolves
# load_index() through probe's module globals, so rebinding the attribute is sufficient.
# Verified byte-identical retrieval vs mmap=False over 135 live queries / 1350 docs
# (seed0_i0, 2026-07-08). Cuts peak footprint per pair process from 5.06 GB to 0.92 GB.
def _load_index_mmap():
    if probe._retriever is None:
        r = bm25s.BM25.load("bm25s_index", load_corpus=True, mmap=True)
        probe._retriever = r
        probe._corpus = r.corpus
    return probe._retriever

probe.load_index = _load_index_mmap

def assert_mmap():
    """Fail loudly rather than silently loading a 5 GB private copy of the index."""
    import numpy as np
    probe.load_index()
    if not isinstance(probe._retriever.scores["data"], np.memmap):
        raise RuntimeError("BM25 score arrays are not memmapped — mmap patch did not take")
    if type(probe._corpus).__name__ != "JsonlCorpus":
        raise RuntimeError(f"corpus is {type(probe._corpus).__name__}, expected JsonlCorpus (mmap)")

MODEL = "openai/gpt-4.1-mini"
K = 3
M = 6
NUM_THREADS = 4
PAIR_TRIPWIRE = 3.00  # per-process backstop (supervisor enforces the real cumulative tripwire)
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
    if _COST["usd"] > PAIR_TRIPWIRE:
        raise RuntimeError(f"PER-PAIR TRIPWIRE ${_COST['usd']:.3f} > ${PAIR_TRIPWIRE}")
litellm.success_callback = [_wire_cb]

def seed_of(*parts):
    return int(hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:8], 16)

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

def _fbmap(metric_fn, pred_name, predictor):
    def feedback_fn(predictor_output, predictor_inputs, module_inputs, module_outputs, captured_trace):
        o = metric_fn(module_inputs, module_outputs, captured_trace, pred_name,
                      [(predictor, predictor_inputs, predictor_output)])
        if hasattr(o, "feedback"):
            if o["feedback"] is None:
                o["feedback"] = f"This trajectory got a score of {o['score']}."
            return o
        return dict(score=o, feedback=f"This trajectory got a score of {o}.")
    return feedback_fn

def load_seed(seed):
    d = os.path.join(S1, f"stage1_seed{seed}")
    gr = json.load(open(os.path.join(d, "gepa_result.json")))
    tm = json.load(open(os.path.join(d, "trainset_manifest.json")))
    graded = {r["threehop_idx"]: r for r in (orjson.loads(l) for l in open(os.path.join(S1, "graded_records.jsonl"), "rb"))}
    train = [graded[tid] for tid in tm["train_threehop_ids"]]
    events = [e for e in gr["full_program_trace"] if e.get("new_subsample_scores")]
    return d, gr, tm, train, events

def reflect_in_instr(seed_dir, event_ordinal):
    from gepa.strategies.instruction_proposal import InstructionProposalSignature as IPS
    T = IPS.default_prompt_template
    pre, rest = T.split("<curr_instructions>"); mid, _ = rest.split("<inputs_outputs_feedback>")
    txt = open(os.path.join(seed_dir, f"reflect_in_{event_ordinal+1}.txt"), encoding="utf-8").read()
    return txt[len(pre):].split(mid, 1)[0]

def byte_verify(t):
    from gepa.strategies.instruction_proposal import InstructionProposalSignature as IPS
    T = IPS.default_prompt_template
    pre, rest = T.split("<curr_instructions>"); mid, post = rest.split("<inputs_outputs_feedback>")
    if not (t.startswith(pre) and t.endswith(post) and mid in t):
        return False
    inner = t[len(pre):len(t)-len(post)]; I, B = inner.split(mid, 1)
    return T.replace("<curr_instructions>", I).replace("<inputs_outputs_feedback>", B) == t \
        and B.startswith("# Example 1") and all(k in B for k in ["## Inputs", "## Generated Outputs", "## Feedback"])

def multiset_match(target, cand_list):
    from itertools import combinations
    tgt = sorted(target); best = None
    for combo in combinations(range(len(cand_list)), 3):
        ms = sorted(cand_list[i] for i in combo)
        key = (0 if ms == tgt else 1, sum(abs(a-b) for a, b in zip(ms, tgt)))
        if best is None or key < best[0]:
            best = (key, combo, key[1], ms == tgt)
    return best[1], best[2], best[3]

def sub_batch(eb, idxs, EB):
    return EB(outputs=[eb.outputs[i] for i in idxs], scores=[eb.scores[i] for i in idxs],
             trajectories=[eb.trajectories[i] for i in idxs] if eb.trajectories else None)

def setup(dspy):
    from gepa.strategies.instruction_proposal import InstructionProposalSignature as IPS
    probe._load_env()
    assert_mmap()  # before any spend: confirm the index is memory-mapped
    student = build_student(dspy)
    metric = make_metric(dspy)
    prednames = [n for n, _ in student.named_predictors()]
    task_lm = dspy.LM(MODEL, max_tokens=3000, cache=False)
    reflection_lm = dspy.LM(MODEL, temperature=1.0, max_tokens=4000, cache=False)
    dspy.configure(lm=task_lm)
    plan = {(r["seed"], r["trace_i"]): r for r in (json.loads(l) for l in open(os.path.join(OUT, "pairing_plan.jsonl")))}
    return dict(dspy=dspy, student=student, metric=metric, prednames=prednames,
                reflection_lm=reflection_lm, plan=plan, IPS=IPS)

def run_one_pair(ctx, seed, trace_i, outdir):
    dspy = ctx["dspy"]; IPS = ctx["IPS"]
    from dspy.teleprompt.gepa.gepa_utils import DspyAdapter, EvaluationBatch
    os.makedirs(outdir, exist_ok=True)
    _COST["usd"] = 0.0
    d, gr, tm, train, events = load_seed(seed)
    ordinal = next(k for k, e in enumerate(events) if e["i"] == trace_i)
    ev = events[ordinal]
    pr = ctx["plan"][(seed, trace_i)]
    parent_cand = gr["program_candidates"][ev["selected_program_candidate"]]
    finstr = reflect_in_instr(d, ordinal)
    comp = next((n for n in ctx["prednames"] if parent_cand.get(n) == finstr), None)
    if comp is None:
        raise RuntimeError(f"component match failed seed{seed} trace_i{trace_i}")
    A_pos, A_par_logged, draw6 = pr["A_e_pos"], pr["A_e_parent_scores"], pr["draw6_pos"]
    def ex(pos): return dspy.Example(claim=train[pos]["claim"], titles=train[pos]["gold"]).with_inputs("claim")
    A_e = [ex(p) for p in A_pos]; cand6 = [ex(p) for p in draw6]

    t0 = time.time()
    adapter = DspyAdapter(student_module=ctx["student"], metric_fn=ctx["metric"],
                          feedback_map={k: _fbmap(ctx["metric"], k, p) for k, p in ctx["student"].named_predictors()},
                          failure_score=0.0, num_threads=NUM_THREADS, add_format_failure_as_feedback=False,
                          rng=random.Random(seed_of(seed, trace_i)), reflection_lm=ctx["reflection_lm"],
                          reflection_minibatch_size=3)
    eb6 = adapter.evaluate(cand6, parent_cand, capture_traces=True)
    combo, l1, exact = multiset_match(A_par_logged, list(eb6.scores))
    B_idx = list(combo); B_pos = [draw6[i] for i in B_idx]
    B_par_fresh = [eb6.scores[i] for i in B_idx]
    ebB = sub_batch(eb6, B_idx, EvaluationBatch); B_e = [cand6[i] for i in B_idx]
    ebA = adapter.evaluate(A_e, parent_cand, capture_traces=True)

    draws_f = open(os.path.join(outdir, "draws.jsonl"), "w")
    for arm, eb in {"SAME": ebA, "SWAP": ebB}.items():
        adapter.rng = random.Random(seed_of(seed, trace_i, arm))
        rd = adapter.make_reflective_dataset(parent_cand, eb, [comp])
        reflect_in = IPS.prompt_renderer({"current_instruction_doc": parent_cand[comp], "dataset_with_feedback": rd[comp]})
        if not byte_verify(reflect_in):
            raise RuntimeError(f"reflect_in byte-verify FAILED seed{seed} trace_i{trace_i} {arm}")
        open(os.path.join(outdir, f"reflect_in_{arm}.txt"), "w", encoding="utf-8").write(reflect_in)
        for draw in range(K):
            raw = ctx["reflection_lm"](reflect_in)
            text = raw[0] if isinstance(raw, list) else raw
            text = text.get("text") if isinstance(text, dict) else text
            child_instr = IPS.output_extractor(str(text))["new_instruction"]
            child_cand = {**parent_cand, comp: child_instr}
            sA = adapter.evaluate(A_e, child_cand, capture_traces=False).scores
            sB = adapter.evaluate(B_e, child_cand, capture_traces=False).scores
            draws_f.write(json.dumps({
                "seed": seed, "trace_i": trace_i, "comp": comp, "arm": arm, "draw": draw,
                "draw_seed": seed_of(seed, trace_i, arm, draw), "child_instruction": child_instr,
                "scores_on_A_e": [float(x) for x in sA], "scores_on_B_e": [float(x) for x in sB],
                "A_e_pos": A_pos, "B_e_pos": B_pos,
                "A_e_parent_scores_logged": A_par_logged, "B_e_parent_scores_fresh": [float(x) for x in B_par_fresh],
                "match_exact": exact, "match_l1": l1,
            }) + "\n"); draws_f.flush()
    draws_f.close()
    meta = {"seed": seed, "trace_i": trace_i, "event_ordinal": ordinal, "comp": comp,
            "parent_candidate_idx": ev["selected_program_candidate"], "A_e_pos": A_pos, "B_e_pos": B_pos,
            "A_e_parent_scores_logged": A_par_logged, "B_e_parent_scores_fresh": [float(x) for x in B_par_fresh],
            "match_exact": exact, "match_l1": l1, "n_draws": 2 * K,
            "pair_cost_usd": round(_COST["usd"], 5), "pair_wall_s": round(time.time() - t0, 1)}
    json.dump(meta, open(os.path.join(outdir, "meta.json"), "w"), indent=2)
    return meta

def main():
    import dspy
    if "--validate" in sys.argv:
        ctx = setup(dspy)
        for seed, ordinal in SMOKE_PAIRS:
            _, gr, _, _, events = load_seed(seed)
            ev = events[ordinal]
            print(f"seed{seed} ev{ordinal} trace_i={ev['i']} parent_idx={ev['selected_program_candidate']}")
        return
    if "--pair" in sys.argv:
        i = sys.argv.index("--pair")
        seed, trace_i = int(sys.argv[i+1]), int(sys.argv[i+2])
        ctx = setup(dspy)
        outdir = os.path.join(OUT, "pairs", f"seed{seed}_i{trace_i}")
        meta = run_one_pair(ctx, seed, trace_i, outdir)
        print(f"PAIR_OK seed{seed}_i{trace_i} cost=${meta['pair_cost_usd']} wall={meta['pair_wall_s']}s "
              f"comp={meta['comp']} match_exact={meta['match_exact']}")
        return
    # legacy 5-pair smoke
    ctx = setup(dspy); total = 0.0
    allrows = open(os.path.join(OUT, "smoke_draws.jsonl"), "w")
    for seed, ordinal in SMOKE_PAIRS:
        _, _, _, _, events = load_seed(seed); trace_i = events[ordinal]["i"]
        outdir = os.path.join(OUT, "pairs", f"seed{seed}_i{trace_i}")
        meta = run_one_pair(ctx, seed, trace_i, outdir)
        for l in open(os.path.join(outdir, "draws.jsonl")):
            allrows.write(l)
        total += meta["pair_cost_usd"]
        print(f"pair seed{seed}_i{trace_i} done ${meta['pair_cost_usd']} cum ${total:.4f}")
    allrows.close()

if __name__ == "__main__":
    main()
