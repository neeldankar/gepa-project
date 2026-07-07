# Scorer portability — IFBench → HoVer/HotpotQA

How each implemented selection scorer would carry to a multi-hop retrieval benchmark. Tagging rule
(per brief): **agnostic** = reads SI text or a generic per-example scalar score; **IFBench-specific**
= references constraints / constraint-ids / constraint-types / failures / the per-constraint binary
matrix. HoVer has no constraints — it has claims + gold documents + hops + retrieval recall/precision
+ SUPPORTED/NOT_SUPPORTED, so IFBench-specific scorers need a retrieval-side reimplementation.

| # | scorer | signal it reads | agnostic / IFBench-specific | HoVer analog | port |
|---|--------|-----------------|------------------------------|--------------|------|
| 1 | input_typicality | TF-IDF of the example INPUT text vs valset inputs | **agnostic** | claim-text typicality vs valset claims | **port as-is** |
| 2 | typicality_x_headroom | input embedding × valset-neighbor frontier deficit | **agnostic** (input text + valset scalar scores) | same; valset scores exist on any benchmark | **port as-is** |
| 3 | pool_disagreement_voi | variance of candidate valset scalar scores at input-neighbors | **agnostic** | same (candidate × valset score matrix) | **port as-is** |
| 4 | output_repairability | length/structure/completeness of the model OUTPUT text | **agnostic** | answer/justification structure | **port as-is** |
| 5 | output_n_words | word count of the OUTPUT text | **agnostic** | answer length | **port as-is** |
| 6 | leverage (probe) | candidate × valset scalar score matrix (SVD column leverage) | **agnostic** | identical — any benchmark with a candidate×example score matrix | **port as-is** |
| 7 | constraint_tractability | Σ over FAILED constraints of (1 − per-type fail-rate) | **IFBench-specific** | per-hop / per-gold-doc-TYPE difficulty (retrieval fail-rate by hop or doc category) | **needs reimpl** |
| 8 | valset_prevalence | Σ over failed constraints of valset prevalence(id) | **IFBench-specific** | prevalence of a gold-doc / entity / hop-type across the valset | **needs reimpl** |
| 9 | prevalence_x_headroom | valset prevalence(id) × frontier deficit | **IFBench-specific** + scalar | gold-doc prevalence × valset frontier deficit | **needs reimpl** |
| 10 | parent_near_frontier | failed-constraint overlap with frontier-opportunity valset specs | **IFBench-specific** + scalar | missed-gold-doc overlap with near-frontier valset claims | **needs reimpl** |
| 11 | coverage_gap | is each failed constraint addressed in the parent prompt (keyword matcher) | **IFBench-specific** + SI text | does the prompt teach the retrieval strategy for the missed gold-doc / next hop | **needs reimpl** |
| 12 | coverage_gap_x_prevalence | ABSENT-from-prompt × valset prevalence | **IFBench-specific** | uncovered-retrieval-strategy × gold-doc prevalence | **needs reimpl** |
| 13 | seed_to_parent_regression | constraints the SEED passed but PARENT now fails | **IFBench-specific** | gold-docs the seed retrieved but the parent now MISSES (recall regression) — clean retrieval analog | **needs reimpl** |

### Never-implemented (prose-only in PROJECT_STATE §7 — no code)
embedding-kNN novelty, NCD/compression distance, actionability-as-specificity, novelty×actionability
→ **n/a — not implemented** (would all be agnostic SI-text scorers if built, but the IFBench finding
"SI is a templated checklist" is what ruled them out; on HoVer/HotpotQA, SI = retrieved-doc lists +
question/claim text + recall diagnostics, which has real variance, so these *could* be worth building
there).

**Stub-plans for HotpotQA (NOT BUILT — what each would read off HotpotQA SI):**
- **embedding-kNN novelty** — embed the example's question + retrieved-passage text; score novelty =
  embedding distance to the nearest already-sampled examples → oversample novel queries / retrieval
  patterns. (Reads: question + retrieved-doc text.) *not built — stub only.*
- **NCD/compression distance** — normalized compression distance between this example's
  retrieved-context (or question) and the pool of seen contexts → retrieval-pattern diversity, no
  embedder needed. (Reads: retrieved-passage / question text.) *not built — stub only.*
- **actionability-as-specificity** — score how specifically the SI names the failure: doc-recall<1
  with a named missed gold doc / identifiable wrong hop (actionable) vs a vague wrong-answer with full
  recall (not). (Reads: the F1/EM + gold_docs/retrieved/recall feedback string.) *not built — stub only.*
- **novelty×actionability** — product of embedding-novelty and actionability → a novel query whose
  failure is specifically diagnosable (the highest-value re-exposure). (Reads: both of the above.)
  *not built — stub only.*

## Verdict
- **Port as-is: 6** — input_typicality, typicality_x_headroom, pool_disagreement_voi,
  output_repairability, output_n_words, leverage (all read input/output text or generic valset
  scalar scores; no constraint machinery).
- **Need reimplementation: 7** — every constraint-keyed scorer; each HAS a clean retrieval-side
  analog (per-hop difficulty, gold-doc prevalence, missed-gold-doc coverage/recall-regression), so
  none are dead-ends, but each must be rebuilt against gold-docs/hops instead of constraint-ids.
- **No analog: 0** among implemented scorers. The survivor `constraint_tractability` is in the
  needs-reimpl bucket — its HoVer analog (per-hop/gold-doc-type difficulty) is the natural thing to
  re-screen on a second benchmark.
