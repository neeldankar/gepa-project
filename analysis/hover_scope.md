# HoVer-proper viability scope — corpus + adapter feasibility

Dry scope only ($0, no model calls, nothing downloaded/built). HoVer = open-domain multihop claim
verification, BM25 over Wikipedia, program `HoverMultiHop` (3-hop, 2 query-writer + 2 doc-summary),
feedback TEXT = "correct documents retrieved + documents remaining to be retrieved". The recurrent
gold-doc-set SI is the reason to prefer HoVer over HotpotQA-distractor.

## Blocker 1 — CORPUS: **BLOCKED** (download needed) / indexing **PARTIAL**
- **Artifact (1a):** HoVer's pre-built **`wiki_wo_links.db` SQLite** corpus — 2017 enwiki,
  **5,486,211 abstracts** — from `https://nlp.cs.unc.edu/data/hover/wiki_wo_links.db`. Plus
  `{train,dev,test}_tfidf_doc_retrieval_results.json` (precomputed TF-IDF candidate sets). Claims/labels
  from HF `hover`. HoVer has **no inline passages** (unlike HotpotQA-distractor) → the full corpus +
  a retriever are mandatory.
- **Cached locally? (1b):** **NO** — only 20 KB of HF `hover` metadata (claims/labels) on disk; the
  corpus is absent.
- **Download size (1c):** **2.01 GB** exactly (`Content-Length` = 2,156,273,664 bytes, confirmed via
  HEAD — not downloaded) + TF-IDF JSONs (~few hundred MB). **Total ≈ 2.0–2.5 GB.**
- **Disk (1d): PASS** — **286 GB free**; corpus (2 GB) + BM25 index (~1–3 GB) is a rounding error.
- **Indexing (1e): PARTIAL** — `rank_bm25` (installed, pure-python, **in-memory**) holds the whole
  tokenized corpus in RAM → **impractical for 5.49M docs on 16 GB RAM**. **Java is absent → pyserini
  (Lucene) unusable** without a JDK install. The $0 route is **bm25s** (pure-python, scipy-sparse/mmap,
  **no JVM** — confirmed installs & imports here, v0.3.9): build over 5.49M abstracts ≈ **~10–20 min,
  ~1–3 GB index**. So indexing is feasible but needs bm25s, not the currently-installed retriever.

## Blocker 2 — ADAPTER / PROGRAM: **BLOCKED**, effort **LARGE**
- **(2a)** GEPA ships **no HoVer adapter** (10 adapters; only `GenericRAGAdapter` is RAG-capable).
- **(2b)** `GenericRAGAdapter` does **single-pass** retrieval (`execute_rag`: reformulate→retrieve→
  rerank→synthesize→answer, **no hop loop**); it optimizes 4 one-shot components and **cannot be
  configured or subclassed** into a 3-hop / 2-query-writer + 2-summary pipeline (the loop is hardcoded,
  no per-hop trajectory). DSPy is **not installed** (the canonical HoverMultiHop reference is the DSPy
  tutorial — would need install + port). **Zero** HoverMultiHop references exist in `gepa`/`gepa-project`.
  → A new **`HoverMultiHopAdapter` + program must be written from scratch**.
- **(2c) Feedback module:** GenericRAGAdapter's feedback is **binary/generic** (`score>0.7` strings)
  and does **NOT** track which gold docs were retrieved vs missed. The "correct docs retrieved + docs
  remaining to be retrieved" SI — the entire reason we want HoVer — **must be written** (gold-doc-id
  tracking per hop → set difference → feedback text). Without it the scorers have nothing to read.

## Blocker 3 — SCORER RE-WIRE: **cheap**, unblocked once 1+2 clear
On HoVer's recurrent gold-doc-set SI (cross-ref `analysis/scorer_portability.md`):
- The **7 reimpl** scorers gain *real, recurrent* signal: `valset_prevalence` → gold-doc prevalence
  across claims; `seed_to_parent_regression` → docs the seed retrieved but the parent now misses
  (recall regression); `constraint_tractability` → per-hop / per-gold-doc retrieval difficulty;
  `coverage_gap` → does the prompt teach retrieving the missed gold-doc set.
- The **4 never-built semantic** scorers (embedding-kNN novelty, NCD, actionability, novelty×action.)
  become **worth building** — HoVer SI ("docs remaining", claim text) has real variance, unlike the
  IFBench templated checklist that killed them.
- The **6 port-as-is** (input_typicality, typicality_x_headroom, pool_disagreement_voi,
  output_repairability, output_n_words, leverage) work mechanically (read claim/answer text or valset
  scalars). Effort: **SMALL–MEDIUM** (~½ day) once the gold-doc feedback exists.

## Bottom line — is HoVer-proper viable?
**Viable in principle, but it is a real build, not a config.** Nothing is fundamentally impossible:
disk is ample and a $0 BM25 path exists (bm25s). The cost is engineering, concentrated in Blocker 2.

**Ordered TODO + rough effort:**
1. Download corpus `wiki_wo_links.db` (**2.0 GB**) + TF-IDF JSONs + HF claims — ~30–60 min, $0.
2. `uv pip install bm25s`; build BM25 index over 5.49M abstracts — **~10–20 min, ~1–3 GB** ($0).
3. Write **`HoverMultiHopAdapter`** + 3-hop loop + 2 query-writer + 2 summary modules + per-hop
   trajectory — **LARGE, ~2–3 days dev**.
4. Write the **feedback module** ("correct docs retrieved + docs remaining") — **MEDIUM, ~½ day**
   (part of the LARGE above; it is the SI we care about).
5. Re-wire the 7 reimpl scorers (+ optionally build the 4 semantic) against gold-doc SI — **~½ day**.
6. THEN run gated baselines (separate spend decision).

**Comparison line:** HoVer-proper setup ≈ **~2.0 GB download + ~15 min bm25s index + ~2–3 days
adapter/feedback engineering (LARGE, write-from-scratch)** before any LLM run; **HotpotQA-distractor
is runnable now at ~$0.35 baseline** but has **thinner SI** (per-example distractor passages; gold-doc
sets don't recur across examples the way HoVer's do, so the curriculum-relevant SI is weaker).

**Recommendation:** if the goal is the richest cross-benchmark SI, HoVer is worth the ~2–3 day build
and the corpus is no longer the wall (2 GB + bm25s, not API embeddings). If the goal is a quick
cheap second-benchmark SI eyeball, HotpotQA-distractor is ready now. The decision is engineering-time
(HoVer) vs SI-richness (HotpotQA), not a blocked-vs-unblocked infra question.
