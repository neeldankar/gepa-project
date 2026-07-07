"""Parts 2-4: 3-hop HoVer program (lifted from the dspy tutorial), retriever dry test, the
docs-remaining SI constructor, and a bounded (<= $0.50) 10-claim run that dumps real HoVer SI.

  .venv/bin/python probe.py            # Part 2: dry test (NO LLM) + feedback unit test
  .venv/bin/python probe.py --run      # Part 3: bounded 10-claim run (gpt-4.1-mini, spend-capped)
"""
import os, sys, time, orjson
import bm25s, Stemmer

N_CLAIMS = 10
NUM_DOCS, NUM_HOPS = 10, 3
SPEND_CAP = 0.50
STOP_AT = 0.45  # early-stop margin
PRICE_IN, PRICE_OUT = 0.40e-6, 1.60e-6  # gpt-4.1-mini per token

stemmer = Stemmer.Stemmer("english")
_retriever = None
_corpus = None


def load_index():
    global _retriever, _corpus
    if _retriever is None:
        r = bm25s.BM25.load("bm25s_index", load_corpus=True)
        _retriever = r
        _corpus = r.corpus
    return _retriever


def search(query: str, k: int = NUM_DOCS):
    r = load_index()
    toks = bm25s.tokenize(query, stopwords="en", stemmer=stemmer, show_progress=False)
    docs, scores = r.retrieve(toks, k=k, n_threads=1, show_progress=False)
    out = []
    for d in docs[0]:
        if isinstance(d, dict):           # bm25s returns corpus records when loaded with corpus
            text = d.get("text", "")
        else:                              # or integer indices
            rec = _corpus[d]
            text = rec["text"] if isinstance(rec, dict) else rec
        out.append(text)
    return out


def title_of(passage: str) -> str:
    return passage.split(" | ", 1)[0].strip()


def build_si(gold_titles, retrieved_titles) -> str:
    """The SI: correct docs retrieved + docs remaining to be retrieved (pure set logic, $0)."""
    gold, got = set(gold_titles), set(retrieved_titles)
    correct = sorted(gold & got)
    remaining = sorted(gold - got)
    return (f"Correctly retrieved {len(correct)}/{len(gold)} gold documents: {correct}. "
            f"Documents remaining to be retrieved: {remaining}.")


def load_threehop():
    return [orjson.loads(l) for l in open("threehop.jsonl")]


def dry_test():
    ex = load_threehop()
    print("=== PART 2: retriever dry test (NO LLM) ===")
    for e in ex[:3]:
        hits = search(e["claim"], k=NUM_DOCS)
        titles = [title_of(h) for h in hits]
        recall = len(set(e["titles"]) & set(titles)) / len(e["titles"])
        print(f"claim: {e['claim'][:80]}")
        print(f"  gold: {e['titles']}")
        print(f"  retrieved@{NUM_DOCS} titles[:6]: {titles[:6]}  gold-recall@{NUM_DOCS}={recall:.2f}")
        print(f"  SI -> {build_si(e['titles'], titles)}")
    # unit test the feedback constructor
    assert "remaining to be retrieved: ['B']" in build_si(["A", "B"], ["A"])
    assert build_si(["A"], ["A"]).count("remaining to be retrieved: []") == 1
    print("feedback constructor unit test: PASS")


def _load_env():
    for line in open("../../.env"):
        if line.startswith("OPENAI_API_KEY"):
            os.environ["OPENAI_API_KEY"] = line.split("=", 1)[1].strip().strip('"')


def run():
    import dspy
    _load_env()
    lm = dspy.LM("openai/gpt-4.1-mini", max_tokens=3000)
    dspy.configure(lm=lm)

    gen_query = dspy.ChainOfThought("claim, notes -> query")
    append_notes = dspy.ChainOfThought("claim, notes, context -> new_notes: list[str], titles: list[str]")

    ex = load_threehop()[:N_CLAIMS]
    print(f"=== PART 3: bounded run, {len(ex)} claims, gpt-4.1-mini, cap ${SPEND_CAP} ===")

    def spend():
        tot = 0.0
        for h in lm.history:
            u = h.get("usage") or {}
            tot += u.get("prompt_tokens", 0) * PRICE_IN + u.get("completion_tokens", 0) * PRICE_OUT
        return tot

    records, done = [], 0
    for e in ex:
        if spend() > STOP_AT:
            print(f"[stop-early] spend ${spend():.4f} near cap before claim {done+1}")
            break
        notes, per_hop = [], []
        for hop in range(NUM_HOPS):
            q = gen_query(claim=e["claim"], notes=notes).query
            ctx = search(q, k=NUM_DOCS)
            ret_titles = [title_of(c) for c in ctx]
            per_hop.append({"hop": hop + 1, "query": q, "retrieved_titles": ret_titles})
            pred = append_notes(claim=e["claim"], notes=notes, context=ctx)
            notes.extend(pred.new_notes if isinstance(pred.new_notes, list) else [str(pred.new_notes)])
        all_ret = sorted({t for h in per_hop for t in h["retrieved_titles"]})
        records.append({"claim": e["claim"], "gold_titles": e["titles"], "per_hop": per_hop,
                        "all_retrieved": all_ret, "si": build_si(e["titles"], all_ret)})
        done += 1
        print(f"  [{done}] spend ${spend():.4f} | {e['claim'][:60]} | SI: {records[-1]['si'][:120]}")

    actual = spend()
    orjson.dumps(records) and open("records.jsonl", "wb").write(b"\n".join(orjson.dumps(r) for r in records))
    write_deliverable(records, actual)
    print(f"\nDONE: {done} claims, actual spend ${actual:.4f}")


def write_deliverable(records, actual):
    gold_counts = {}
    for r in records:
        for t in r["gold_titles"]:
            gold_counts[t] = gold_counts.get(t, 0) + 1
    recurring = {t: c for t, c in gold_counts.items() if c > 1}
    L = ["# HoVer SI sample — the eyeball test\n",
         f"{len(records)} HoVer 3-hop claims run through the DSPy multi-hop program (gpt-4.1-mini, "
         f"BM25 over 5.23M wiki abstracts). Verbatim docs-remaining SI strings.\n"]
    for i, r in enumerate(records):
        L.append(f"### [{i}] {r['claim']}")
        L.append(f"- gold titles: {r['gold_titles']}")
        L.append(f"- retrieved (union over 3 hops): {r['all_retrieved'][:12]}{' …' if len(r['all_retrieved'])>12 else ''}")
        L.append(f"- **SI:** {r['si']}\n")
    n_unique_gold = len(gold_counts)
    n_gold_instances = sum(gold_counts.values())
    L.append("## Note (literal observations)")
    L.append(f"1. SI varies example-to-example: each string lists this claim's own gold/remaining titles "
             "(contrast IFBench's fixed `Satisfied k/n` scaffold).")
    L.append(f"2. Gold-title recurrence across the {len(records)} claims: {n_gold_instances} gold-title "
             f"instances, {n_unique_gold} unique; recurring titles (≥2 claims): {recurring or 'none in this sample'}.")
    L.append(f"3. Content: the SI is structured title LISTS (gold ∩ retrieved, gold − retrieved) — "
             "named Wikipedia article titles, not free-form prose and not a templated checklist.")
    L.append(f"4. Actual spend: ${actual:.4f} (cap ${SPEND_CAP}).")
    open("hover_si_sample.md", "w").write("\n".join(L) + "\n")
    print("wrote hover_si_sample.md")


if __name__ == "__main__":
    if "--run" in sys.argv:
        run()
    else:
        dry_test()
