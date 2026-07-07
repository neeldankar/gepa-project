"""Coverage_gap re-screen under BETTER matchers (brief: test, don't argue).

Two improved matchers vs the original keyword matcher:
  (A) tightened keywords  — split start/end, drop over-generic tokens (letter/language/times/sentence).
  (B) embedding similarity — TF-IDF (fit on system-prompt sentences + per-type canonical descriptions);
      PRESENT if max cosine(type_desc, prompt sentence) > threshold; sweep thresholds.

Recompute coverage_gap (Σ ABSENT*1.0 + PRESENT*0.25) per event under each, aggregate to batch (mean),
re-screen partial-Spearman-vs-LOO + LORO, compare to the original verdict (0.051). Offline, $0.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.scorer_inputs import classify_coverage, constraint_type, reconstruct_prompts, _strip
from gepa_si.screen.screen_scorers import KEYS, aggregate_events, batch_frame, loro_partial, screen_scorer

# Canonical one-line description per constraint TYPE (semantic anchor for the embedding matcher).
TYPE_DESC = {
    "keywords": "include or exclude specific keywords or words a certain number of times",
    "language": "write the entire response in a specific language",
    "length_constraints": "limit the number of words sentences or paragraphs",
    "detectable_content": "include a postscript or placeholder markers in brackets",
    "detectable_format": "use bullet lists sections titles json markdown or highlighted formatting",
    "combination": "give two separate responses or repeat the prompt verbatim",
    "startend": "end the response with a specific phrase or wrap it in quotation marks",
    "change_case": "use all uppercase or all lowercase letters or control capitalization",
    "punctuation": "avoid commas or control punctuation like periods and exclamation marks",
    "copy": "repeat or copy a phrase exactly word for word",
    "new": "copy a span of the input text verbatim by index",
    "paragraphs": "separate the response into paragraphs with dividers",
    "first_word": "begin each sentence or paragraph with a specific first word",
    "last_word": "end each sentence with a specific last word",
    "letters": "control how many times a specific letter appears",
    "count": "count occurrences increments or unique items in the response",
}

# (B') tightened keyword cues — directional, no over-generic single tokens.
TIGHT_CUES = {
    "keywords": ["keyword", "forbidden word", "exclude the word", "include the word", "word frequency",
                 "palindrome", "no two adjacent"],
    "language": ["respond in", "write in the", "output language", "in english", "entirely in"],
    "length_constraints": ["number of words", "number of sentences", "number of paragraphs",
                           "at least", "at most", "no more than", "word count"],
    "detectable_content": ["postscript", "p.s.", "placeholder", "square bracket", "[address]"],
    "detectable_format": ["bullet", "numbered list", "section", "title", "json", "highlight",
                          "markdown", "hyphen", "bigram wrapping"],
    "combination": ["two responses", "two separate responses", "repeat the prompt", "repeat the request"],
    "startend": ["end with", "finish with", "conclude with", "end your response", "in quotation",
                 "wrap your response", "in quotes"],
    "change_case": ["uppercase", "lowercase", "all caps", "all capital", "no capital"],
    "punctuation": ["no comma", "without commas", "no exclamation", "punctuation"],
    "copy": ["repeat the phrase", "copy", "verbatim", "word for word", "exactly as"],
    "new": ["copy the span", "copy a span", "verbatim from the input"],
    "paragraphs": ["paragraph", "divider", "***", "section break"],
    "first_word": ["first word", "begin each sentence", "start each sentence", "begin each paragraph"],
    "last_word": ["last word", "end each sentence", "final word of each"],
    "letters": ["the letter", "letter frequency", "how many times the letter", "letter appears"],
    "count": ["count the", "number of times", "increment", "unique words", "occurrences"],
}

THRESHOLDS = [0.10, 0.15, 0.20, 0.25, 0.30]
ABSENT_W, PRESENT_W = 1.0, 0.25
_SENT = re.compile(r"[.\n!?;:]")


def tight_classify(prompt_lower: str, cid: str) -> str:
    cues = TIGHT_CUES.get(constraint_type(cid), [])
    return "PRESENT" if any(c in prompt_lower for c in cues) else "ABSENT"


class EmbedMatcher:
    def __init__(self, prompts: list[str]):
        sents = []
        for p in prompts:
            sents += [s.strip() for s in _SENT.split(p.lower()) if len(s.strip()) > 3]
        corpus = sents + list(TYPE_DESC.values())
        self.vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True).fit(corpus)
        self.type_vecs = {t: self.vec.transform([d]) for t, d in TYPE_DESC.items()}
        self._cache: dict[int, np.ndarray] = {}

    def max_sim(self, prompt: str, cid: str) -> float:
        h = hash(prompt)
        if h not in self._cache:
            sents = [s.strip() for s in _SENT.split(prompt.lower()) if len(s.strip()) > 3]
            self._cache[h] = self.vec.transform(sents) if sents else None
        S = self._cache[h]
        if S is None or S.shape[0] == 0:
            return 0.0
        tv = self.type_vecs[constraint_type(cid)]
        sims = (S @ tv.T).toarray().ravel()
        return float(sims.max()) if sims.size else 0.0


def coverage_events(runs, label_fn) -> pd.DataFrame:
    rows = []
    for run in runs:
        prompts = reconstruct_prompts(run.log_path)
        for c in run.cycles:
            pl = (prompts.get(c.parent_id) or "")
            for p, failed in enumerate(c.failed_ids_per_example):
                val = sum(ABSENT_W if label_fn(pl, cid) == "ABSENT" else PRESENT_W for cid in failed)
                rows.append({"seed": run.seed, "b": run.b, "iteration": c.iteration,
                             "example_pos": p, "coverage_gap_v": val})
    return pd.DataFrame(rows)


def rescreen(runs, bf, label_fn, name) -> dict:
    ev = coverage_events(runs, label_fn)
    agg = aggregate_events(ev, ["coverage_gap_v"])
    m = bf.merge(agg, on=KEYS, how="left", validate="one_to_one")
    b3 = m[m.b == 3]
    sc = screen_scorer(b3, "coverage_gap_v_mean")
    lo = loro_partial(b3, "coverage_gap_v_mean", "loo_contribution")
    return {"matcher": name, "raw_loo": sc["raw_spear_loo"], "partial_loo": sc["partial_loo"],
            "contam_diff": sc["corr_difficulty"], "loro_mean": lo["loro_mean"], "loro_sd": lo["loro_sd"]}


def main():
    runs = load_corpus()
    bf = batch_frame(runs)
    prompts_all = []
    for run in runs:
        prompts_all += list(reconstruct_prompts(run.log_path).values())
    em = EmbedMatcher(prompts_all)

    results = [rescreen(runs, bf, classify_coverage, "original_keyword")]
    results.append(rescreen(runs, bf, tight_classify, "tightened_keyword"))
    for th in THRESHOLDS:
        results.append(rescreen(runs, bf, lambda pl, cid, th=th: "PRESENT" if em.max_sim(pl, cid) > th else "ABSENT",
                                f"embed_thr{th}"))
    tab = pd.DataFrame(results)
    print("=== coverage_gap RE-SCREEN under better matchers (b3 pooled, vs LOO) ===")
    print(tab.round(3).to_string(index=False))
    print("\nsurvival bar (constraint_tractability): partial_loo 0.172, LORO 0.171")
    best = tab.iloc[tab["partial_loo"].abs().values.argmax()]
    print(f"best matcher: {best['matcher']}  partial_loo={best['partial_loo']:.3f}  "
          f"loro={best['loro_mean']:.3f}")
    tab.to_parquet("analysis/coverage_rescreen.parquet", index=False)


if __name__ == "__main__":
    main()
