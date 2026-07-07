"""Shared static inputs for Phase-1 scorer screening (built once, cached).

Everything here is corpus-static (does not depend on a particular reflection cycle):
  - valset constraint composition + prevalence  (from the HF dataset, offline cache)
  - valset / trainset INPUT text + constraint identity per positional index
  - per-constraint-TYPE corpus fail-rate -> tractability weight (from partial_diag.parquet)
  - TF-IDF (word + char n-gram) embeddings over input text  (sentence-transformers absent)

The event->trainset join is direct: minibatch_ids are POSITIONAL indices into the trainset
(PROJECT_STATE 2), and constraint-id formats match between logs and the dataset
("category:name"). Run offline: HF_DATASETS_OFFLINE=1.
"""

from __future__ import annotations

import functools

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer

from gepa_si.ifrlvr_data import load_faithful_splits
from gepa_si.screen.corpus_io import _load

PARTIAL_DIAG_PARQUET = "analysis/partial_diag.parquet"

# Tractable constraint TYPES (PROJECT_STATE 3, Probe 4) — the live curriculum slice.
TRACTABLE_TYPES = frozenset({
    "detectable_content", "language", "combination", "startend", "change_case", "punctuation",
})


def constraint_type(cid: str) -> str:
    """'keywords:word_once#2' -> 'keywords'. Strips the #idx dedup suffix then the :name."""
    return cid.split("#", 1)[0].split(":", 1)[0]


def _strip(cid: str) -> str:
    """Drop the #idx dedup suffix; keep 'category:name'."""
    return cid.split("#", 1)[0]


# ---------- dataset (valset / trainset) ----------
@functools.lru_cache(maxsize=1)
def _splits() -> tuple[list[dict], list[dict]]:
    return load_faithful_splits()


@functools.lru_cache(maxsize=1)
def valset_meta() -> dict:
    """Static valset facts.

    Returns dict with:
      prevalence: {cid: fraction of the 150 valset specs whose constraint-set contains cid}
      constraint_sets: list[set[str]]   per val_id (positional 0..149)
      inputs: list[str]                 per val_id input text
      val_ids: list[str]                str keys "0".."149" (align to scores_by_val_id)
    """
    _, val = _splits()
    constraint_sets = [{_strip(c) for c in item["instruction_id_list"]} for item in val]
    inputs = [item["input"] for item in val]
    n = len(val)
    counts: dict[str, int] = {}
    for cs in constraint_sets:
        for cid in cs:
            counts[cid] = counts.get(cid, 0) + 1
    prevalence = {cid: k / n for cid, k in counts.items()}
    return {
        "prevalence": prevalence,
        "constraint_sets": constraint_sets,
        "inputs": inputs,
        "val_ids": [str(i) for i in range(n)],
        "n": n,
    }


@functools.lru_cache(maxsize=1)
def trainset_meta() -> dict:
    """Per trainset positional index: input text + constraint id-set. minibatch_ids index this."""
    train, _ = _splits()
    return {
        "inputs": [item["input"] for item in train],
        "constraint_sets": [{_strip(c) for c in item["instruction_id_list"]} for item in train],
        "n": len(train),
    }


def prevalence_of(cid: str) -> float:
    return valset_meta()["prevalence"].get(_strip(cid), 0.0)


# ---------- per-type tractability ----------
@functools.lru_cache(maxsize=1)
def type_failrate() -> dict[str, float]:
    """{type: corpus fail-rate} from partial_diag.parquet (fail = 1 - mean parent_sat)."""
    df = pd.read_parquet(PARTIAL_DIAG_PARQUET)
    g = df.groupby("type")["parent_sat"].mean()
    return {t: float(1.0 - m) for t, m in g.items()}


def tractability_of(cid: str) -> float:
    """1 - fail_rate(type(cid)); tractable types ~1, near-unsatisfiable ~0. Unknown -> 0.5."""
    fr = type_failrate().get(constraint_type(cid))
    return (1.0 - fr) if fr is not None else 0.5


def is_tractable_type(cid: str) -> bool:
    return constraint_type(cid) in TRACTABLE_TYPES


# ---------- TF-IDF embeddings over INPUT text ----------
# NOTE: this embeds the task INPUT prompts (which have real lexical variance), NOT the
# templated SI checklist — so it is NOT one of the dead semantic-text scorers (PROJECT_STATE 7).
@functools.lru_cache(maxsize=1)
def _embedder():
    """Fit word+char TF-IDF on (trainset + valset) inputs; return (matrix-fn, val_matrix)."""
    tr_inputs = trainset_meta()["inputs"]
    val_inputs = valset_meta()["inputs"]
    corpus = tr_inputs + val_inputs
    word_vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)
    word_vec.fit(corpus)
    char_vec.fit(corpus)

    def embed(texts: list[str]):
        m = hstack([word_vec.transform(texts), char_vec.transform(texts)]).tocsr()
        # L2-normalize rows so cosine = dot product
        norms = np.sqrt(m.multiply(m).sum(axis=1)).A1
        norms[norms == 0] = 1.0
        return m.multiply(1.0 / norms[:, None]).tocsr()

    val_mat = embed(val_inputs)
    return embed, val_mat


def embed_inputs(texts: list[str]):
    """L2-normalized word+char TF-IDF rows for arbitrary input texts."""
    embed, _ = _embedder()
    return embed(texts)


def valset_input_matrix():
    """L2-normalized embedding matrix of the 150 valset inputs (rows align to val_id)."""
    _, val_mat = _embedder()
    return val_mat


# ---------- parent prompt-text reconstruction (Wave 2) ----------
def reconstruct_prompts(log_path: str) -> dict[int, str]:
    """{candidate_idx: system_prompt} for a run, from its raw JSONL (PROJECT_STATE 2).

    idx 0 = optimization_start.seed_candidate.system_prompt;
    idx k = the proposal_end.new_instructions.system_prompt in the iteration whose
            candidate_accepted.new_candidate_idx == k.
    Returns only successfully-reconstructed idxs; callers should verify coverage of parent_ids.
    """
    records = _load(log_path)
    out: dict[int, str] = {}
    seed = next((r for r in records if r.get("event") == "optimization_start"), None)
    if seed is not None:
        sp = (seed.get("seed_candidate") or {}).get("system_prompt")
        if sp is not None:
            out[0] = sp
    # group proposal_end / candidate_accepted by iteration
    prop_by_it: dict[int, dict] = {}
    acc_by_it: dict[int, dict] = {}
    for r in records:
        ev, it = r.get("event"), r.get("iteration")
        if it is None:
            continue
        if ev == "proposal_end":
            prop_by_it[it] = r
        elif ev == "candidate_accepted":
            acc_by_it[it] = r
    for it, acc in acc_by_it.items():
        k = acc.get("new_candidate_idx")
        prop = prop_by_it.get(it)
        if k is None or prop is None:
            continue
        sp = (prop.get("new_instructions") or {}).get("system_prompt")
        if sp is not None:
            out[int(k)] = sp
    return out


# ---------- coverage-gap keyword matcher (Wave 2, scorer #8) ----------
# Light keyword/regex cues per constraint TYPE, matched against the evolved system prompt.
# Detects whether the prompt already states a rule addressing the type (PRESENT) or not
# (ABSENT). CONTRADICTORY is not reliably detectable with keywords and NLI is unavailable
# offline, so the matcher does a robust ABSENT/PRESENT split; the 3rd class is left as an
# (unused) slot and reported as such. Cues are intentionally broad — recall over precision,
# since a false PRESENT only makes ABSENT (the high-value signal) more conservative.
_TYPE_CUES: dict[str, list[str]] = {
    "keywords": ["keyword", "the word", "specific word", "forbidden", "exclude", "must include",
                 "must contain", "frequency", "appear", "times", "palindrome", "adjacent"],
    "language": ["language", "respond in", "write in", "in english", "entirely in"],
    "length_constraints": ["sentence", "paragraph", "number of words", "at least", "at most",
                           "exactly", "no more than", "no fewer", "word count"],
    "detectable_content": ["postscript", "p.s", "placeholder", "square bracket", "[ ]", "[address]"],
    "detectable_format": ["bullet", "list", "section", "title", "json", "highlight", "markdown",
                          "format", "hyphen", "square bracket", "wrap", "bigram"],
    "combination": ["two responses", "repeat the prompt", "repeat the request", "verbatim",
                    "second response", "separate response"],
    "startend": ["end with", "start with", "begin with", "conclude", "finish with", "quotation",
                 "wrap your", "in quotes"],
    "change_case": ["uppercase", "lowercase", "capital", "all caps", "letter case", "in caps"],
    "punctuation": ["comma", "punctuation", "period", "exclamation", "no comma", "full stop"],
    "copy": ["copy", "repeat", "verbatim", "exactly as", "word for word"],
    "new": ["copy", "span", "verbatim", "exactly as", "word for word"],
    "paragraphs": ["paragraph", "divider", "***", "separated by", "section break"],
    "first_word": ["first word", "begin each", "start each", "each sentence with"],
    "last_word": ["last word", "end each", "finish each", "each sentence end"],
    "letters": ["letter", "count the letter", "frequency of", "how many times the letter"],
    "count": ["count", "number of times", "increment", "unique", "occurrences", "how many"],
}


@functools.lru_cache(maxsize=1)
def _compiled_cues() -> dict[str, list[str]]:
    # substrings are matched lowercased; no regex needed (kept simple/auditable)
    return {t: [c.lower() for c in cues] for t, cues in _TYPE_CUES.items()}


def classify_coverage(prompt_lower: str, cid: str) -> str:
    """'ABSENT' if the prompt states no rule for cid's type, else 'PRESENT'."""
    cues = _compiled_cues().get(constraint_type(cid), [])
    return "PRESENT" if any(c in prompt_lower for c in cues) else "ABSENT"


def topk_cosine(vec_row, ref_matrix, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Top-k cosine sims of one (normalized) row vs a (normalized) ref matrix.

    Returns (sims_desc, idxs_desc) for the k nearest reference rows.
    """
    sims = (ref_matrix @ vec_row.T).toarray().ravel()
    k = min(k, sims.size)
    idx = np.argpartition(-sims, k - 1)[:k]
    order = np.argsort(-sims[idx])
    idx = idx[order]
    return sims[idx], idx
