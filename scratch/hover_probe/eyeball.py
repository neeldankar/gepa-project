"""Extended HoVer SI eyeball: actionability structure vs page-difficulty, 40 claims (<= $2).

Reuses probe.py (search, title_of, build_si, load_threehop, _load_env). Runs threehop[10:50] through
the 3-hop program, then does $0/no-LLM structural analysis: do MISSED gold docs cluster into rule-able
page-types, and is that independent of difficulty (recall) — or just "obscure page = hard"?

  .venv/bin/python eyeball.py            # Part 0 reuse check (NO LLM)
  .venv/bin/python eyeball.py --run      # Part 1-3: bounded 40-claim run + analysis + deliverable
"""
import os, re, sys, collections
import orjson
import probe  # reuse: load_index, search, title_of, build_si, load_threehop, _load_env

CLAIMS = slice(10, 50)        # distinct from the earlier 0..9
NUM_DOCS, NUM_HOPS = 10, 3
CAP, STOP_AT = 2.00, 1.90
PRICE_IN, PRICE_OUT = 0.40e-6, 1.60e-6  # gpt-4.1-mini

# ---------- structural actionability features (no LLM) ----------
WORK = {"album", "film", "song", "ep", "novel", "band", "tv series", "video game", "play", "opera",
        "soundtrack", "book", "single", "miniseries", "magazine", "newspaper", "musical", "franchise"}
PERSON = {"politician", "footballer", "musician", "singer", "actor", "actress", "author", "writer",
          "director", "producer", "cricketer", "rugby", "boxer", "wrestler", "artist", "painter",
          "composer", "poet", "general", "bishop", "journalist", "presenter", "rapper", "dj"}
PLACE = {"town", "village", "city", "district", "parish", "county", "river", "mountain", "region",
         "province", "state", "neighborhood", "suburb", "hamlet", "civil parish"}
US_STATES = {"alabama","alaska","arizona","arkansas","california","colorado","connecticut","delaware",
             "florida","georgia","hawaii","idaho","illinois","indiana","iowa","kansas","kentucky",
             "louisiana","maine","maryland","massachusetts","michigan","minnesota","mississippi",
             "missouri","montana","nebraska","nevada","ohio","oklahoma","oregon","texas","utah",
             "vermont","virginia","washington","wisconsin","wyoming","new york","new jersey"}
_STOP = {"the","of","a","an","and","in","on","to","for","s"}


def page_type(title: str) -> str:
    t = title.strip()
    low = t.lower()
    if low.startswith("list of") or low.startswith("list "):
        return "LIST"
    if re.search(r"\b(1|2)\d{3}(–|-)\d{2}\b", t) or re.search(r"\b(1|2)\d{3}\b.*(season|election|championship|olympics|cup|tournament|final)", low):
        return "SEASON/EVENT"
    m = re.search(r"\(([^)]+)\)\s*$", t)
    if m:
        paren = m.group(1).strip().lower()
        if any(w in paren for w in WORK):
            return "WORK"
        if any(w in paren for w in PERSON):
            return "PERSON"
        if any(w in paren for w in PLACE):
            return "PLACE"
        return "DISAMBIG-OTHER"
    if re.search(r",\s+[A-Z][a-z]+", t) and (low.split(", ")[-1] in US_STATES or "county" in low or "district" in low):
        return "PLACE"
    return "PLAIN"


def is_disambig(title: str) -> bool:
    return bool(re.search(r"\([^)]+\)\s*$", title.strip()))


def content_tokens(title: str):
    toks = re.findall(r"[a-z0-9]+", title.lower())
    return [w for w in toks if w not in _STOP and len(w) > 1]


# ---------- obscurity: document-frequency of gold-title tokens (one cached-corpus stream) ----------
def token_doc_freq(target_tokens: set) -> dict:
    """Count, over the cached corpus, how many docs contain each target token. $0, low-mem."""
    df = {t: 0 for t in target_tokens}
    path = "bm25s_index/corpus.jsonl"
    n = 0
    with open(path, "rb") as f:
        for line in f:
            n += 1
            try:
                text = orjson.loads(line).get("text", "")
            except Exception:
                continue
            present = set(re.findall(r"[a-z0-9]+", text.lower()))
            for t in target_tokens:
                if t in present:
                    df[t] += 1
    return df, n


def part0():
    probe.load_index()
    hits = probe.search("test query about a wikipedia article", k=5)
    ex = probe.load_threehop()
    print(f"PART 0 reuse check: index loaded, search returned {len(hits)} docs, "
          f"threehop has {len(ex)} claims -> READY")


def run():
    import dspy
    probe._load_env()
    lm = dspy.LM("openai/gpt-4.1-mini", max_tokens=3000)
    dspy.configure(lm=lm)
    gen_query = dspy.ChainOfThought("claim, notes -> query")
    append_notes = dspy.ChainOfThought("claim, notes, context -> new_notes: list[str], titles: list[str]")

    ex = probe.load_threehop()[CLAIMS]
    # cost projection
    proj = len(ex) * NUM_HOPS * (400*PRICE_IN + 60*PRICE_OUT + 2200*PRICE_IN + 250*PRICE_OUT)
    print(f"PART 1: {len(ex)} claims (threehop[{CLAIMS.start}:{CLAIMS.stop}]); projected ${proj:.3f} (cap ${CAP})")
    if proj > CAP:
        ex = ex[:int(CAP/ (proj/len(ex)))]
        print(f"  projection>cap -> reduced to {len(ex)} claims")

    def spend():
        tot = 0.0
        for h in lm.history:
            u = h.get("usage") or {}
            tot += u.get("prompt_tokens", 0)*PRICE_IN + u.get("completion_tokens", 0)*PRICE_OUT
        return tot

    records = []
    for e in ex:
        if spend() > STOP_AT:
            print(f"[stop-early] spend ${spend():.4f} near cap")
            break
        notes, per_hop = [], []
        for hop in range(NUM_HOPS):
            q = gen_query(claim=e["claim"], notes=notes).query
            ctx = probe.search(q, k=NUM_DOCS)
            rt = [probe.title_of(c) for c in ctx]
            per_hop.append({"hop": hop+1, "query": q, "retrieved_titles": rt})
            pred = append_notes(claim=e["claim"], notes=notes, context=ctx)
            notes.extend(pred.new_notes if isinstance(pred.new_notes, list) else [str(pred.new_notes)])
        allret = sorted({t for h in per_hop for t in h["retrieved_titles"]})
        gold = e["titles"]; missed = sorted(set(gold) - set(allret))
        recall = len(set(gold) & set(allret)) / len(gold)
        records.append({"claim": e["claim"], "gold": gold, "per_hop": per_hop, "all_retrieved": allret,
                        "missed": missed, "recall": recall, "si": probe.build_si(gold, allret)})
        print(f"  [{len(records)}] ${spend():.4f} recall={recall:.2f} missed={missed} | {e['claim'][:50]}")
    actual = spend()
    open("eyeball_records.jsonl", "wb").write(b"\n".join(orjson.dumps(r) for r in records))
    analyze(records, actual)


def analyze(records, actual):
    # obscurity: doc-freq of all gold-title tokens (one corpus pass)
    gold_tokens = set()
    for r in records:
        for t in r["gold"]:
            gold_tokens.update(content_tokens(t))
    print(f"\nPART 2: computing corpus doc-freq for {len(gold_tokens)} gold-title tokens (one pass)...")
    df, ncorpus = token_doc_freq(gold_tokens)

    def obscurity(title):  # mean log-rarity of content tokens; higher = rarer
        toks = content_tokens(title)
        import math
        vals = [math.log10(ncorpus / max(1, df.get(t, 0)+1)) for t in toks]
        return sum(vals)/len(vals) if vals else 0.0

    # per-missed-doc features + per-claim rows
    bucket_hist = collections.Counter()
    rows = []
    miss_records = []  # (page_type, is_disambig, obscurity, claim_recall)
    for r in records:
        miss_types = []
        for m in r["missed"]:
            pt = page_type(m); bucket_hist[pt] += 1
            miss_types.append(pt)
            miss_records.append({"title": m, "page_type": pt, "disambig": is_disambig(m),
                                 "obscurity": obscurity(m), "recall": r["recall"],
                                 # difficulty axis = miss DEPTH (avoids the 2/3<0.67 float artifact):
                                 # deep-miss claim = missed >=2 of its gold docs; near-miss = missed exactly 1
                                 "hard": len(r["missed"]) >= 2})
        rows.append({"claim": r["claim"][:46], "ngold": len(r["gold"]), "recall": r["recall"],
                     "nrem": len(r["missed"]), "miss_types": miss_types,
                     "disambig": any(is_disambig(m) for m in r["missed"]),
                     "obsc": round(sum(obscurity(m) for m in r["missed"])/max(1,len(r["missed"])), 2)})

    # retrieved (non-missed) gold obscurity for contrast
    ret_obsc = [obscurity(t) for r in records for t in r["gold"] if t not in r["missed"]]
    miss_obsc = [mr["obscurity"] for mr in miss_records]

    # 2x2 cross-tab: structural marker (LIST/SEASON/WORK/PERSON/PLACE/DISAMBIG-OTHER = structured) x difficulty
    structured = lambda pt: pt != "PLAIN"
    ct = collections.Counter()
    for mr in miss_records:
        ct[(structured(mr["page_type"]), mr["hard"])] += 1

    write_md(records, rows, bucket_hist, miss_records, ct, miss_obsc, ret_obsc, actual)
    print(f"\nDONE: {len(records)} claims, {len(miss_records)} missed docs, actual ${actual:.4f}")


def write_md(records, rows, bucket_hist, miss_records, ct, miss_obsc, ret_obsc, actual):
    import statistics as st
    n = len(records); nmiss = len(miss_records)
    nplain = bucket_hist.get("PLAIN", 0)
    structured = nmiss - nplain
    mean_miss_obsc = round(st.mean(miss_obsc), 2) if miss_obsc else 0
    mean_ret_obsc = round(st.mean(ret_obsc), 2) if ret_obsc else 0
    L = ["# HoVer SI extended eyeball — actionability vs page-difficulty\n",
         f"{n} HoVer 3-hop claims (threehop[10:50]) through the DSPy multi-hop program (gpt-4.1-mini, "
         f"BM25 over 5.23M wiki abstracts). Actionability features are pure title-structure ($0, no LLM).\n"]

    # representative SI spread (sort by recall, take a spread)
    bysorted = sorted(records, key=lambda r: r["recall"])
    pick = bysorted[:4] + bysorted[len(bysorted)//2-1:len(bysorted)//2+2] + bysorted[-3:]
    L.append("## ~10 verbatim SI strings (spread across recall)\n")
    for r in pick:
        L.append(f"- recall={r['recall']:.2f} | **SI:** {r['si']}")
    L.append("")

    L.append("## Page-type histogram of ALL missed gold docs (Part 2c — the key check)\n")
    L.append(f"- total missed docs: **{nmiss}**  |  PLAIN (no structural marker): **{nplain}** "
             f"({100*nplain/max(1,nmiss):.0f}%)  |  structured: **{structured}** ({100*structured/max(1,nmiss):.0f}%)")
    for b, c in bucket_hist.most_common():
        L.append(f"  - {b}: {c}")
    L.append("")

    L.append("## Actionability × difficulty cross-tab (Part 2d)\n")
    L.append("Missed docs, `structured page-type (≠PLAIN)` × miss-depth of the claim "
             "(deep = the claim missed ≥2 of 3 gold docs; near = missed exactly 1):\n")
    L.append("| | deep-miss (≥2 missed) | near-miss (1 missed) |")
    L.append("|---|---|---|")
    L.append(f"| **structured** | {ct[(True,True)]} | {ct[(True,False)]} |")
    L.append(f"| **PLAIN** | {ct[(False,True)]} | {ct[(False,False)]} |")
    L.append(f"\nMean obscurity (log10 corpus-rarity of title tokens): **missed {mean_miss_obsc}** vs "
             f"**retrieved-gold {mean_ret_obsc}** (higher = rarer).\n")

    L.append("## Full 40-claim feature table\n")
    L.append("| claim | recall | n_rem | missed page-types | disambig | mean_obsc |")
    L.append("|---|---|---|---|---|---|")
    for r in rows:
        L.append(f"| {r['claim']} | {r['recall']:.2f} | {r['nrem']} | "
                 f"{','.join(r['miss_types']) or '—'} | {'Y' if r['disambig'] else ''} | {r['obsc']} |")
    L.append("")

    # honest verdict
    frac_struct = structured/max(1, nmiss)
    struct_in_near = ct[(True, False)]   # structured misses in near-miss (easier) claims
    obsc_gap = mean_miss_obsc - mean_ret_obsc
    L.append("## 5-line HONEST verdict (literal)\n")
    L.append(f"1. **Cluster into rule-able page-types?** {structured}/{nmiss} ({100*frac_struct:.0f}%) "
             f"missed docs have a structural marker; {nplain} ({100*nplain/max(1,nmiss):.0f}%) are PLAIN "
             "bare names. " + ("Mostly PLAIN one-offs → weak rule-able structure." if frac_struct < 0.5
             else "A recognizable fraction is structured → some rule-able structure."))
    L.append(f"2. **Independent of difficulty?** structured misses in NEAR-miss (1-missed) claims = "
             f"{struct_in_near} (vs {ct[(True,True)]} in deep-miss). " + ("Structure appears off the "
             "deep-miss tail → not purely difficulty." if struct_in_near >= 2 else
             "Structure concentrates in deep-miss claims → largely collinear with difficulty."))
    L.append(f"3. **Obscurity collision:** missed-gold obscurity {mean_miss_obsc} vs retrieved-gold "
             f"{mean_ret_obsc} (Δ={obsc_gap:+.2f}). " + ("Misses are markedly rarer → 'obscure=missed' difficulty channel is real."
             if obsc_gap > 0.3 else "Misses are NOT much rarer → obscurity alone doesn't explain misses."))
    L.append(f"4. **Actual spend:** ${actual:.4f} (cap ${CAP}).")
    lean = ("LEAN NO-GO" if (frac_struct < 0.4 or struct_in_near < 2) else "LEAN WEAK-GO")
    L.append(f"5. **Go/no-go lean (not a decision):** {lean} — "
             + ("missed-doc actionability looks mostly like page-difficulty/obscurity with little "
                "title-structure a scorer could exploit beyond difficulty; the cheap null is not refuted."
                if lean == "LEAN NO-GO" else
                "there is some difficulty-independent structure in missed-doc types; a fuller screen "
                "could be worth funding, but the signal is modest — confirm on more claims first."))
    open("hover_si_eyeball.md", "w").write("\n".join(L) + "\n")
    print("wrote hover_si_eyeball.md")


def analyze_only():
    """Re-run the $0 structural analysis on the saved records — NO LLM calls."""
    records = [orjson.loads(l) for l in open("eyeball_records.jsonl")]
    spent = 0.1891  # actual spend of the run that produced eyeball_records.jsonl
    analyze(records, spent)


if __name__ == "__main__":
    if "--run" in sys.argv:
        run()
    elif "--analyze" in sys.argv:
        analyze_only()
    else:
        part0()
