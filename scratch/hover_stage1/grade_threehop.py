"""Stage-1 Step A — grade a FRESH threehop slice to build an imperfect (recall<1.0) trainset pool.

Grader logic lifted from ../hover_probe/eyeball.py run(): SAME seed 3-hop program (gen_query +
append_notes ChainOfThought), SAME retrieval (NUM_DOCS=10, NUM_HOPS=3), SAME model (gpt-4.1-mini).
"imperfect" == imperfect for the exact program the GEPA run optimizes. Slice starts at threehop
index 50 (disjoint from probe.py's [0:10] and eyeball.py's [10:50]).

Grading is per-claim independent and deterministic (dspy default temp 0), so after a 5-claim
sequential CALIBRATION smoke (measured $/claim + s/claim), the remainder is graded in parallel
(threads, per-thread dspy.context) purely to cut wall-clock — results are identical to sequential.
The GEPA run in Step B stays num_threads=1, identical to the frozen reference.

  ../hover_probe/.venv/bin/python grade_threehop.py
"""
from __future__ import annotations
import os, sys, time, json, threading
from concurrent.futures import ThreadPoolExecutor

HOVER_PROBE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "hover_probe"))
OUT_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, HOVER_PROBE)
os.chdir(HOVER_PROBE)  # probe's relative paths (bm25s_index/, threehop.jsonl, ../../.env)
import orjson
import probe  # noqa: E402

START = 50                 # disjoint from frozen threehop[10:50]
MAX_GRADE = 400            # ceiling on #claims graded (slice [50:450])
TARGET_IMPERFECT = 110     # stop once this many recall<1.0 claims (N_TRAIN<=100 + N_VAL 10)
WORKERS = 8
CHUNK = 24                 # parallel batch size; bounds target overshoot
NUM_DOCS, NUM_HOPS = probe.NUM_DOCS, probe.NUM_HOPS
PRICE_IN, PRICE_OUT = probe.PRICE_IN, probe.PRICE_OUT
CAP = 3.00

RECORDS_PATH = os.path.join(OUT_DIR, "graded_records.jsonl")
SUMMARY_PATH = os.path.join(OUT_DIR, "graded_summary.json")


def main():
    import dspy
    probe._load_env()
    lm = dspy.LM("openai/gpt-4.1-mini", max_tokens=3000)
    dspy.configure(lm=lm)
    gen_query = dspy.ChainOfThought("claim, notes -> query")
    append_notes = dspy.ChainOfThought("claim, notes, context -> new_notes: list[str], titles: list[str]")

    ex = probe.load_threehop()
    n_total = len(ex)
    end = min(START + MAX_GRADE, n_total)
    print(f"threehop={n_total}; slice [{START}:{end}] target={TARGET_IMPERFECT} imperfect cap=${CAP}",
          flush=True)

    def spend():
        tot = 0.0
        for h in list(lm.history):
            u = h.get("usage") or {}
            tot += u.get("prompt_tokens", 0) * PRICE_IN + u.get("completion_tokens", 0) * PRICE_OUT
        return tot

    def grade_one(idx):
        e = ex[idx]
        with dspy.context(lm=lm):
            notes, per_hop = [], []
            for hop in range(NUM_HOPS):
                q = gen_query(claim=e["claim"], notes=notes).query
                ctx = probe.search(q, k=NUM_DOCS)
                rt = [probe.title_of(c) for c in ctx]
                per_hop.append({"hop": hop + 1, "query": q, "retrieved_titles": rt})
                pred = append_notes(claim=e["claim"], notes=notes, context=ctx)
                notes.extend(pred.new_notes if isinstance(pred.new_notes, list) else [str(pred.new_notes)])
        allret = sorted({t for h in per_hop for t in h["retrieved_titles"]})
        gold = e["titles"]
        missed = sorted(set(gold) - set(allret))
        recall = len(set(gold) & set(allret)) / len(gold) if gold else 0.0
        return {"threehop_idx": idx, "claim": e["claim"], "gold": gold, "per_hop": per_hop,
                "all_retrieved": allret, "missed": missed, "recall": recall,
                "si": probe.build_si(gold, allret)}

    t0 = time.time()
    out = open(RECORDS_PATH, "wb")
    wlock = threading.Lock()
    records, n_imperfect = [], 0

    def commit(rec):
        nonlocal n_imperfect
        with wlock:
            records.append(rec)
            out.write(orjson.dumps(rec) + b"\n"); out.flush()
            if rec["recall"] < 1.0:
                n_imperfect += 1

    # ---- CALIBRATION: 5 claims sequential, measured ----
    for idx in range(START, min(START + 5, end)):
        commit(grade_one(idx))
    el, sp = time.time() - t0, spend()
    calib = {"claims": len(records), "elapsed_s": round(el, 2), "spend_usd": round(sp, 4),
             "s_per_claim": round(el / max(1, len(records)), 2),
             "usd_per_claim": round(sp / max(1, len(records)), 5),
             "imperfect_in_smoke": n_imperfect}
    print(f"[CALIB @{len(records)}] {calib['s_per_claim']}s/claim ${calib['usd_per_claim']}/claim "
          f"({n_imperfect}/{len(records)} imperfect) -> proj {MAX_GRADE}cl seq="
          f"{calib['s_per_claim']*MAX_GRADE/60:.1f}min ${calib['usd_per_claim']*MAX_GRADE:.2f}; "
          f"parallel x{WORKERS}", flush=True)

    # ---- remainder: parallel in chunks, early-stop on target/cap ----
    rest = list(range(START + len(records), end))
    stopped = None
    with ThreadPoolExecutor(max_workers=WORKERS) as exsvc:
        for c0 in range(0, len(rest), CHUNK):
            if n_imperfect >= TARGET_IMPERFECT:
                stopped = "target"; break
            if spend() > CAP:
                stopped = "cap"; break
            chunk = rest[c0:c0 + CHUNK]
            for rec in exsvc.map(grade_one, chunk):
                commit(rec)
            print(f"  graded={len(records)} imperfect={n_imperfect} ${spend():.4f} "
                  f"{(time.time()-t0)/60:.1f}min", flush=True)
    out.close()

    elapsed, actual = time.time() - t0, spend()
    imperfect = [r for r in records if r["recall"] < 1.0]
    from collections import Counter
    summary = {
        "slice_start": START, "slice_end_attempted": end, "graded": len(records),
        "imperfect": len(imperfect), "perfect": len(records) - len(imperfect),
        "imperfect_ids": sorted(r["threehop_idx"] for r in imperfect),
        "spend_usd": round(actual, 4), "elapsed_s": round(elapsed, 1),
        "stopped_reason": stopped or "slice_exhausted",
        "calibration_at_5": calib,
        "recall_hist": {str(round(k, 3)): v
                        for k, v in sorted(Counter(round(r["recall"], 3) for r in records).items())},
    }
    json.dump(summary, open(SUMMARY_PATH, "w"), indent=2)
    print("\n===== GRADE SUMMARY =====", flush=True)
    print(json.dumps({k: v for k, v in summary.items() if k != "imperfect_ids"}, indent=2), flush=True)
    print(f"graded {len(records)} -> {len(imperfect)} imperfect  ${actual:.4f}  {elapsed/60:.1f}min",
          flush=True)


if __name__ == "__main__":
    main()
