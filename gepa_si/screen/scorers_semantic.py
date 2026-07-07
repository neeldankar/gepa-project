"""Reopened SEMANTIC scorers on the CORRECT reflection object (full triple).

Every prior 'semantic' scorer was computed on the per-example **Feedback string**, which is
id-determined (templated from the failed-constraint checklist) — hence the prior collapse.
The proposer actually reads the full triple (Inputs + Generated Outputs + Feedback); the
**Generated Outputs are NOT id-determined**, so the collapse argument does not transfer. We
rebuild four never-built semantic scorers + a new output failure-MODE signature, each computed
THREE ways:
    (a) on the Feedback string only   -> reproduces the thin-object baseline/null
    (b) on the full triple            -> what the proposer sees  (the honest candidate)
    (c) delta (b - a)                 -> the signal the Output/Input actually added

All features are LOCAL / model-free ($0; no API embeddings):
  - knn_novelty   : 1 - mean cosine sim to k nearest neighbors, word+char TF-IDF (lexical
                    stand-in for sentence embeddings; true embeddings are a paid Wave-2 variant)
  - ncd_novelty   : mean normalized-compression-distance (zlib) to the k nearest of a fixed
                    deterministic reference sample — the model-free novelty analogue
  - actionability : density of concrete specificity markers (digits, quoted spans, format cues)
  - nov_x_act     : knn_novelty * actionability
  - failure_mode  : [NEW] output-pathology texture, parsed from Generated Outputs CONDITIONED on
                    the failed constraint (count/length near-miss, format-present-but-wrong,
                    truncated postscript) — distinct from the id-keyed failure-signature (dead)
                    and from output_repairability #11 (generic, constraint-agnostic).

Reference pool for novelty = all 1251 per-example units (b3+b1); the screen later restricts to
b3. $0, pure log reading + local CPU.
"""

from __future__ import annotations

import re
import zlib

import numpy as np
import pandas as pd
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer

from gepa_si.screen.corpus_io import RunData, load_corpus
from gepa_si.screen.scorer_inputs import constraint_type
from gepa_si.screen.triples_io import Triple, extract_reflection_triples

EVENT_KEYS = ["seed", "b", "iteration", "example_pos"]

# scorer base names; each gets _a (feedback), _b (full triple), _delta (b-a). failure_mode is
# output-derived and has no feedback variant -> single column.
SEMANTIC_BASES = ["knn_novelty", "ncd_novelty", "actionability", "nov_x_act"]
SEMANTIC_COLS = [f"{b}_{v}" for b in SEMANTIC_BASES for v in ("a", "b", "delta")] + ["failure_mode"]

K_NN = 5
N_NCD_REF = 64
K_NCD = 5


# --------------------------------------------------------------------------- collect units
def collect_units(runs: list[RunData]) -> pd.DataFrame:
    """One row per (seed,b,iteration,example_pos): feedback / full / outputs text + failed_ids.

    example_pos is aligned to corpus_io's failed_ids_per_example (the same join the built
    scorers use), so this matrix merges 1:1 onto analysis/scorers.parquet.
    """
    rows = []
    for run in runs:
        trip = extract_reflection_triples(run)
        for c in run.cycles:
            tl = trip.get(c.iteration, [])
            for p, failed in enumerate(c.failed_ids_per_example):
                t = tl[p] if p < len(tl) else Triple("", "", "")
                rows.append({
                    "seed": run.seed, "b": run.b, "iteration": c.iteration, "example_pos": p,
                    "feedback": t.feedback, "full": t.full(), "outputs": t.outputs,
                    "failed_ids": list(failed),
                })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- TF-IDF kNN novelty
def _tfidf_matrix(texts: list[str]):
    safe = [t if t.strip() else " " for t in texts]
    word = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    char = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)
    W = word.fit_transform(safe)
    C = char.fit_transform(safe)
    M = hstack([W, C]).tocsr()
    norms = np.sqrt(M.multiply(M).sum(axis=1)).A1
    norms[norms == 0] = 1.0
    return M.multiply(1.0 / norms[:, None]).tocsr()


def knn_novelty(texts: list[str], k: int = K_NN) -> np.ndarray:
    """1 - mean cosine sim to the k nearest OTHER units. High = lexically novel/atypical."""
    M = _tfidf_matrix(texts)
    S = (M @ M.T).toarray()
    np.fill_diagonal(S, -np.inf)  # exclude self
    kk = min(k, S.shape[0] - 1)
    topk = np.partition(S, -kk, axis=1)[:, -kk:]
    return 1.0 - topk.mean(axis=1)


# --------------------------------------------------------------------------- NCD novelty
def _clen(b: bytes) -> int:
    return len(zlib.compress(b, 6))


def ncd_novelty(texts: list[str], n_ref: int = N_NCD_REF, k: int = K_NCD) -> np.ndarray:
    """Mean NCD to the k nearest of a fixed strided reference sample. High = compression-novel."""
    data = [t.encode("utf-8", "ignore") if t.strip() else b" " for t in texts]
    Cx = np.array([_clen(d) for d in data], dtype=float)
    n = len(data)
    ref = np.unique(np.linspace(0, n - 1, min(n_ref, n)).round().astype(int))
    nov = np.zeros(n)
    for i in range(n):
        di, ci = data[i], Cx[i]
        ds = []
        for j in ref:
            if j == i:
                continue
            cj = Cx[j]
            mx = max(ci, cj)
            if mx <= 0:
                ds.append(0.0)
                continue
            cxy = _clen(di + data[j])
            ds.append((cxy - min(ci, cj)) / mx)
        if ds:
            dsa = np.sort(np.asarray(ds))[:k]  # k nearest = k smallest NCD
            nov[i] = float(dsa.mean())
    return nov


# --------------------------------------------------------------------------- actionability
_DIGIT = re.compile(r"\d")
_QUOTE = re.compile(r"\"[^\"]+\"|'[^']+'|<<[^>]+>>|\[[^\]]+\]")
# single-word concrete format / constraint cues (specificity markers), matched on word
# boundaries (so 'word' does not also count inside 'keyword'/'words').
_CUE_WORDS = [
    "json", "bullet", "bullets", "list", "section", "sections", "title", "paragraph",
    "paragraphs", "sentence", "sentences", "word", "words", "letter", "letters", "uppercase",
    "lowercase", "capital", "comma", "commas", "punctuation", "postscript", "placeholder",
    "highlight", "highlighted", "quotation", "verbatim", "keyword", "exactly", "forbidden",
    "format", "markdown", "bracket", "brackets", "hyphen", "palindrome",
]
_CUE_RE = re.compile(r"\b(?:" + "|".join(_CUE_WORDS) + r")\b")

# Normalize per 100 CHARACTERS (robust to no-space code outputs that have few tokens) with a
# length floor so tiny strings can't explode the density.
_LEN_FLOOR = 200.0


def actionability(text: str) -> float:
    """Density (markers per 100 chars) of concrete specificity markers. High = specific."""
    if not text.strip():
        return 0.0
    low = text.lower()
    n_digit = len(_DIGIT.findall(text))
    n_quote = len(_QUOTE.findall(text))
    n_cue = len(_CUE_RE.findall(low))
    denom = max(len(text), _LEN_FLOOR)
    return 100.0 * (n_digit + n_quote + n_cue) / denom


# --------------------------------------------------------------------------- failure-MODE [new]
_FB_LINE = re.compile(r"[✗✓]\s*\[([^\]]+)\]\s*(FAILED|satisfied)\s*[—-]\s*(.*)")
_SENT_SPLIT = re.compile(r"[.!?]+")
_BULLET = re.compile(r"(?m)^\s*([-*•]|\d+[.)])\s+")
_HEADER = re.compile(r"(?m)^\s*(#{1,6}\s+|\*\*.+\*\*\s*$)")
_FENCE = re.compile(r"```")

# constraint types whose requirement is an integer COUNT we can re-count in the output
_COUNT_COUNTERS = {
    "length_constraints": "auto",   # paragraphs/sentences/words inferred from the description
    "detectable_format": "auto",
    "count": "auto",
    "paragraphs": "paragraphs",
}
# format/content types where "structure present but wrong" is the near-miss signal
_FORMAT_TYPES = frozenset({"detectable_format", "detectable_content", "startend", "paragraphs"})


def _count_thing(desc_low: str, out: str) -> tuple[int, int] | None:
    """(required_int, actual_count) for a length/count constraint, or None if unparseable."""
    m = re.search(r"\b(\d+)\b", desc_low)
    if not m:
        return None
    req = int(m.group(1))
    if "paragraph" in desc_low:
        actual = len([p for p in re.split(r"\n\s*\n", out) if p.strip()])
    elif "sentence" in desc_low:
        actual = len([s for s in _SENT_SPLIT.split(out) if s.strip()])
    elif "word" in desc_low:
        actual = len(out.split())
    elif "bullet" in desc_low or "list" in desc_low:
        actual = len(_BULLET.findall(out))
    elif "section" in desc_low or "highlight" in desc_low:
        actual = len(_HEADER.findall(out))
    else:
        return None
    return req, actual


def _structure_present(out: str) -> bool:
    return bool(_FENCE.search(out) or _BULLET.search(out) or _HEADER.search(out)
                or "[" in out or "p.s" in out.lower() or "{" in out)


def _near_miss(cid: str, desc: str, out: str) -> float:
    """1.0 if this failed constraint looks like a locally-repairable near-miss, else 0.0."""
    typ = constraint_type(cid)
    desc_low = desc.lower()
    if typ in _COUNT_COUNTERS or "length_constraints" in typ:
        cnt = _count_thing(desc_low, out)
        if cnt is not None:
            req, actual = cnt
            tol = max(2, int(np.ceil(0.2 * req)))
            return 1.0 if abs(actual - req) <= tol else 0.0
    if typ in _FORMAT_TYPES:
        return 1.0 if _structure_present(out) else 0.0
    return 0.0


def failure_mode(feedback: str, outputs: str, failed_ids: list[str]) -> float:
    """Fraction of the example's FAILED constraints that read as near-miss / repairable.

    Conditioned on each failed constraint's requirement (parsed from its Feedback line) and the
    actual Generated Output. 0 if nothing failed or nothing classifiable.
    """
    if not failed_ids:
        return 0.0
    # map failed cid -> its description from the feedback checklist
    desc_by_cid: dict[str, str] = {}
    for line in feedback.splitlines():
        m = _FB_LINE.search(line)
        if m and m.group(2) == "FAILED":
            desc_by_cid[m.group(1).split("#", 1)[0]] = m.group(3)
    flags = [_near_miss(cid, desc_by_cid.get(cid.split("#", 1)[0], ""), outputs) for cid in failed_ids]
    return float(np.mean(flags)) if flags else 0.0


# --------------------------------------------------------------------------- build matrix
def build_semantic_matrix(runs: list[RunData] | None = None) -> pd.DataFrame:
    if runs is None:
        runs = load_corpus()
    u = collect_units(runs)
    fb = u["feedback"].tolist()
    fl = u["full"].tolist()

    # novelty, two variants (a=feedback, b=full triple)
    knn_a, knn_b = knn_novelty(fb), knn_novelty(fl)
    ncd_a, ncd_b = ncd_novelty(fb), ncd_novelty(fl)
    act_a = np.array([actionability(t) for t in fb])
    act_b = np.array([actionability(t) for t in fl])
    nxa_a, nxa_b = knn_a * act_a, knn_b * act_b

    fmode = np.array([
        failure_mode(f, o, ids)
        for f, o, ids in zip(u["feedback"], u["outputs"], u["failed_ids"])
    ])

    out = u[EVENT_KEYS].copy()
    cols = {
        "knn_novelty_a": knn_a, "knn_novelty_b": knn_b, "knn_novelty_delta": knn_b - knn_a,
        "ncd_novelty_a": ncd_a, "ncd_novelty_b": ncd_b, "ncd_novelty_delta": ncd_b - ncd_a,
        "actionability_a": act_a, "actionability_b": act_b, "actionability_delta": act_b - act_a,
        "nov_x_act_a": nxa_a, "nov_x_act_b": nxa_b, "nov_x_act_delta": nxa_b - nxa_a,
        "failure_mode": fmode,
    }
    for c, v in cols.items():
        out[c] = v
    return out
