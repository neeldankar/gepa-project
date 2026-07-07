"""Batch-swap v2 — PAID run (2x2 reflect x gate). GATED on analysis/ablation/APPROVED_V2 (Neel-only).

For each B-batch: parent P_B is the single baseline. Failure-matched B' (>=2 of B''s 3 examples fail under
P_B). Two reflect arms x k draws = 4 children, EACH gated on BOTH B and B' (6 examples). All four estimand
margins use P_B as baseline: P_B-on-B (step 2) and P_B-on-B' (the failure-match eval, capture_traces=True,
so it also yields R_B''s reflection objects). Checkpoint-resumable, retry<=3 logged, $55 tripwire.

  .venv/bin/python scripts/batch_swap_v2_run.py --smoke   # 1 pair (~$0.10)
  .venv/bin/python scripts/batch_swap_v2_run.py           # full (~$29, cap $60)
"""
from __future__ import annotations

import csv, hashlib, json, os, random, re, sys, time
from dotenv import load_dotenv

load_dotenv()

OUT = "analysis/ablation/batch_swap_v2"
APPROVAL = "analysis/ablation/APPROVED_V2"
K = 3
SPEND_CAP = 55.0
MAX_CAND = 6          # failure-match search breadth per B (bounds search cost)
COMP = "system_prompt"
SMOKE = "--smoke" in sys.argv

# ---- HARD GATE: refuse without the Neel-only approval file ------------------------------------------
if not os.path.exists(APPROVAL):
    sys.exit(f"REFUSING TO START: {APPROVAL} does not exist. Only Neel creates it after reading plan.md.")
_mtime = os.path.getmtime(APPROVAL)
print(f"APPROVED_V2 present (mtime={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(_mtime))}) — proceeding.")
if not os.environ.get("OPENAI_API_KEY", "").strip():
    sys.exit("ERROR: OPENAI_API_KEY not set")

from gepa.lm import LM
from gepa.adapters.default_adapter.default_adapter import DefaultAdapter
from gepa.strategies.instruction_proposal import InstructionProposalSignature
from gepa_si.ifbench_eval import IFConstraintEvaluator
from gepa_si.ifrlvr_data import load_faithful_splits
from gepa_si.screen.corpus_io import load_corpus, discover_runs, _load

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


def seed_of(*parts):
    return int(hashlib.md5("|".join(map(str, parts)).encode()).hexdigest()[:8], 16)


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
                m = re.search(r"perform a task for me:\n```\n(.*?)\n```\n",
                              r["prompts"]["system_prompt"], re.S)
                if m:
                    out[(cfg["seed"], r["iteration"])] = m.group(1)
    return out


def main():
    from gepa_si.screen.scorer_inputs import trainset_meta, constraint_type
    os.makedirs(OUT, exist_ok=True)
    trainset, _ = load_faithful_splits()
    curr = load_curr()
    tm = trainset_meta(); csets = tm["constraint_sets"]
    types_of = lambda tid: {constraint_type(c) for c in csets[tid]}

    runs = [r for r in load_corpus() if r.b == 3]
    batches, terc = {}, {}
    import numpy as np
    for r in runs:
        its = sorted(c.iteration for c in r.cycles); q1, q2 = np.quantile(its, [1/3, 2/3])
        for c in r.cycles:
            batches[(r.seed, c.iteration)] = list(c.minibatch_ids)
            terc[(r.seed, c.iteration)] = 0 if c.iteration <= q1 else (1 if c.iteration <= q2 else 2)
    allb = [b for b in sorted(batches) if b in curr]

    # projected fail order (from frozen corpus) to make the failure-match search hit on the first try
    projfail = {}
    for r in runs:
        for c in r.cycles:
            for p, tid in enumerate(c.minibatch_ids):
                projfail.setdefault(tid, []).append(1.0 if c.before_scores[p] < 1.0 else 0.0)
    projfail = {t: float(np.mean(v)) for t, v in projfail.items()}

    # timeout=180 so a dead/hung socket (network blip or laptop-sleep-severed TCP) raises instead of
    # blocking forever; litellm num_retries + the retry() wrapper then recover on a fresh connection.
    # Operational robustness only — identical API calls, no effect on the experiment's logic/seeds.
    refl = LM("openai/gpt-4.1", timeout=180)
    adapter = DefaultAdapter(model="openai/gpt-4.1-mini", evaluator=IFConstraintEvaluator(),
                             litellm_batch_completion_kwargs={"timeout": 180})

    def spend():
        return float(refl.total_cost) + float(adapter._lm.total_cost)

    # eval cache keyed by (parent_key, tuple(example_ids)) -> (scores list, objects list). Counts hits.
    ecache = {}
    stat = {"eval_req": 0, "eval_run": 0}

    def parent_eval(pkey, P, ids):
        stat["eval_req"] += 1
        key = (pkey, tuple(ids))
        if key not in ecache:
            stat["eval_run"] += 1
            ex = [trainset[t] for t in ids]
            eb = retry(lambda: adapter.evaluate(ex, {COMP: P}, capture_traces=True), f"peval {pkey}")
            objs = list(adapter.make_reflective_dataset({COMP: P}, eb, [COMP])[COMP])
            ecache[key] = (list(eb.scores), objs)
        return ecache[key]

    # ---------- STEP 2-3: failure-matched pairing (durable checkpoint = pairing.csv) ----------
    pairing_path = f"{OUT}/pairing{'_smoke' if SMOKE else ''}.csv"
    if os.path.exists(pairing_path):
        pairs = list(csv.DictReader(open(pairing_path)))
        print(f"resume: loaded {len(pairs)} pairs from {pairing_path}")
    else:
        pairs, drops = [], []
        order = sorted(allb, key=lambda B: seed_of(20260703, B))
        if SMOKE:
            order = order[:1]
        for B in order:
            s = B[0]; bset = set(batches[B]); bt = set().union(*[types_of(t) for t in batches[B]])
            pkey = f"s{B[0]}_it{B[1]}"; P = curr[B]
            b_scores, _ = parent_eval(pkey, P, batches[B])            # P_B on B (baseline + fail scores)
            cands = [X for X in allb if X != B and X[0] == s and terc[X] == terc[B]
                     and not (set(batches[X]) & bset)]
            cands.sort(key=lambda X: -sum(projfail[t] for t in batches[X]))
            chosen = None
            for X in cands[:MAX_CAND]:
                xs, _ = parent_eval(pkey, P, batches[X])              # P_B on candidate B' (cached)
                if sum(sc < 1.0 for sc in xs) >= 2:
                    chosen = X; break
            if chosen is None:
                drops.append(B); continue
            xt = set().union(*[types_of(t) for t in batches[chosen]])
            xs, _ = ecache[(pkey, tuple(batches[chosen]))]
            pairs.append({
                "B_id": pkey, "Bprime_id": f"s{chosen[0]}_it{chosen[1]}",
                "seed": B[0], "iteration": B[1], "tercile": terc[B],
                "Bprime_seed": chosen[0], "Bprime_iteration": chosen[1],
                "type_jaccard": round(len(bt & xt) / max(len(bt | xt), 1), 4),
                "B_fail_underPB": sum(sc < 1.0 for sc in b_scores),
                "Bprime_fail_underPB": sum(sc < 1.0 for sc in xs),
                "parent_B_sum": round(sum(b_scores), 4), "parent_Bp_sum": round(sum(xs), 4),
                "B_ids": json.dumps(batches[B]), "Bprime_ids": json.dumps(batches[chosen]),
            })
            if spend() > SPEND_CAP:
                sys.exit(f"!!! TRIPWIRE during pairing ${spend():.2f}")
        with open(pairing_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(pairs[0].keys())); w.writeheader(); w.writerows(pairs)
        hitrate = 1 - stat["eval_run"] / max(stat["eval_req"], 1)
        print(f"PAIRING done: {len(pairs)} pairs, {len(drops)} drops, cache-hit {hitrate:.2f}, "
              f"spend ${spend():.4f}. Wrote {pairing_path} BEFORE any proposer call.", flush=True)
        if drops:
            print("  dropped B (no failure-matched B'):", [f"s{b[0]}_it{b[1]}" for b in drops])

    # ---------- STEP 5: 2x2 children (checkpoint = calls.csv; 2K rows per complete pair) ----------
    calls_path = f"{OUT}/calls{'_smoke' if SMOKE else ''}.csv"
    done = {}
    if os.path.exists(calls_path):
        for r in csv.DictReader(open(calls_path)):
            done[r["B_id"]] = done.get(r["B_id"], 0) + 1
        fh = open(calls_path, "a", newline=""); cw = csv.writer(fh)
        print(f"resume: {sum(1 for v in done.values() if v >= 2*K)} pairs already complete")
    else:
        fh = open(calls_path, "w", newline=""); cw = csv.writer(fh)
        cw.writerow(["B_id", "Bprime_id", "arm", "draw", "draw_seed",
                     "child_sum_B", "child_sum_Bp", "parent_B_sum", "parent_Bp_sum",
                     "margin_on_B", "margin_on_Bp", "cum_spend"])
    fh.flush()

    n_new = 0
    for row in pairs:
        Bid = row["B_id"]
        if done.get(Bid, 0) >= 2 * K:
            continue
        B = (int(row["seed"]), int(row["iteration"]))
        P = curr[B]; pkey = Bid
        B_ids = json.loads(row["B_ids"]); Bp_ids = json.loads(row["Bprime_ids"])
        B_ex = [trainset[t] for t in B_ids]; Bp_ex = [trainset[t] for t in Bp_ids]
        b_scores, objs_B = parent_eval(pkey, P, B_ids)       # R_B reflects on B's objects
        bp_scores, objs_Bp = parent_eval(pkey, P, Bp_ids)    # R_B' reflects on B''s objects
        pB_sum, pBp_sum = float(sum(b_scores)), float(sum(bp_scores))
        prompts = {"R_B": build_prompt(P, objs_B), "R_Bp": build_prompt(P, objs_Bp)}
        seq = [(arm, d) for arm in ("R_B", "R_Bp") for d in range(K)]
        random.Random(seed_of("order", Bid)).shuffle(seq)
        for arm, d in seq:
            ds = seed_of(Bid, arm, d)
            raw = retry(lambda: refl(prompts[arm]), f"proposer {Bid} {arm}{d}")
            child = InstructionProposalSignature.output_extractor(raw)["new_instruction"]
            cB = retry(lambda: adapter.evaluate(B_ex, {COMP: child}, capture_traces=False), "gateB")
            cBp = retry(lambda: adapter.evaluate(Bp_ex, {COMP: child}, capture_traces=False), "gateBp")
            sB, sBp = float(sum(cB.scores)), float(sum(cBp.scores))
            cw.writerow([Bid, row["Bprime_id"], arm, d, ds, round(sB, 4), round(sBp, 4),
                         round(pB_sum, 4), round(pBp_sum, 4),
                         round(sB - pB_sum, 4), round(sBp - pBp_sum, 4), round(spend(), 4)])
            fh.flush()
            if spend() > SPEND_CAP:
                print(f"!!! SPEND TRIPWIRE ${spend():.2f} — ABORT (checkpoint saved)"); fh.close(); sys.exit(2)
        n_new += 1
        if n_new % 10 == 0 or SMOKE:
            print(f"  [{n_new}] pairs done this run, spend ${spend():.4f}", flush=True)
    fh.close()
    print(f"\nDONE {n_new} new pairs. proposer ${refl.total_cost:.4f} + task ${adapter._lm.total_cost:.4f} "
          f"= ${spend():.4f} -> {calls_path}", flush=True)


if __name__ == "__main__":
    main()
