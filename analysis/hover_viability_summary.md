# HoVer viability + scorer portability + IFBench SI — summary

Mostly-$0 read-only investigation. **No OpenAI API call was made.** `logs/phase2/` untouched.

## Part 0 — scorer portability (`analysis/scorer_portability.md`)
13 implemented per-example signals tagged. **6 port as-is** (input_typicality, typicality_x_headroom,
pool_disagreement_voi, output_repairability, output_n_words, leverage — all read input/output text or
generic valset scalar scores). **7 need reimplementation** (every constraint-keyed scorer, incl. the
survivor `constraint_tractability`; each has a clean retrieval-side analog — per-hop / gold-doc-type
difficulty, gold-doc prevalence, missed-gold-doc coverage / recall-regression). **0 have no analog**
among implemented scorers. The 4 "dead semantic" scorers (embedding-kNN, NCD, actionability,
novelty×actionability) are **prose-only, never coded** (n/a).

## Part 1 — IFBench SI is a checklist? **YES** (`analysis/ifbench_si_sample.md`)
10 failed-example `Feedback` strings (seeds 0–4, 11 constraint types) are 100% fixed scaffold
(`Satisfied k/n constraints.` + `✓/✗ [category:id] satisfied|FAILED — <description>`); descriptions
are per-type templates with filled slots. The only thing that varies is which constraint ids appear
and their arguments — no free-form text. It is a checklist (this is why the SI-text scorers were dead).

## Parts 2/3 — viable benchmark: **HotpotQA-distractor** (HoVer not viable)

**HoVer dry standup (a–e):** all fail —
- a) no GEPA HoVer adapter (only `GenericRAGAdapter`, no HoVer loader/program).
- b) **HoVer dataset not cached; Wikipedia corpus absent** — HoVer's enwiki corpus is multi-GB
  (≈ several GB, not downloaded; >2GB so not fetched per the rule).
- c) no local retriever installed; `GenericRAGAdapter` default embeddings = OpenAI API (gated).
- d) blocked by (b)/(c).
- e) `GenericRAGAdapter` imports & instantiates generically, but there is no HoVer program/corpus.
→ **Break point: no harness + corpus absent (multi-GB) + retriever needs API/large index.**

**HotpotQA dry standup (a–e):** boots —
- Loaded cached HotpotQA-distractor via **Arrow-direct** (`Dataset.from_file`); HF script-load is
  broken ("dataset scripts no longer supported"). 7,405 val rows, 10 **inline** passages each.
- a) `GenericRAGAdapter` / `DefaultAdapter` + a thin Arrow loader (written: `scripts/run_hotpot_baseline.py`).
- b) **inline distractor passages → no Wikipedia index needed** (the key win).
- c) `rank_bm25` installed ($0, pure-python); per-example BM25 over the 10 passages built.
- d) retriever dry test: gold supporting-fact titles retrievable; **recall@4 = 0.72** over 200
  random val examples (local, no API).
- e) `DefaultAdapter` + token-F1 evaluator instantiated with **no model call**; loader + evaluator
  exercised offline (gold-as-response → F1 1.0). Script compiles.
→ **HotpotQA-distractor is viable offline at $0 up to the LLM step.**

## GATE — staged, NOT executed

**Exact baseline command** (uniform sampler, small split, modest budget — exists only to generate real
SI to eyeball; `scripts/run_hotpot_baseline.py` is written but **not run**):
```
.venv/bin/python scripts/run_hotpot_baseline.py --n-train 40 --n-val 40 --b 3 --max-metric-calls 300
```
It does BM25 retrieval (top-4, $0) → gpt-4.1-mini answers (token-F1 scored, with gold-doc recall in the
SI) → gpt-4.1 reflection optimizes the answer prompt; logs to `logs/hotpot/`.

**Projected cost** (prices ≈ $0.40/$1.60 per-1M for gpt-4.1-mini, $2/$8 for gpt-4.1):
| item | calls | tokens in/out | $ |
|---|---|---|---|
| task (gpt-4.1-mini) | ~300 | ~650 / ~20 | $0.09 |
| reflection (gpt-4.1) | ~15 | ~2800 / ~1500 | $0.26 |
| **baseline total (nominal)** | | | **~$0.35** |
| baseline conservative (2.5× ctx/reflections) | | | ~$0.71 |
| **smoke test** (≤5 ex, gpt-4.1-mini, no reflection) | 5 | ~650 / ~20 | **<$0.01** |

## Bottom line
Of the 13 scorers, **6 port as-is, 7 need reimplementation (all with retrieval analogs), 0 no-analog**.
IFBench SI is a templated checklist (confirmed). **HoVer is not viable** without a multi-GB Wikipedia
corpus + retriever/harness build; **HotpotQA-distractor boots cleanly at $0** through retrieval and is
the recommended second benchmark for generating real, non-checklist SI.

**Awaiting go-ahead to spend $0.01 (smoke) / ~$0.35–0.75 (baseline).**
