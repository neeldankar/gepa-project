"""Targeted re-screens for the THRESHOLD-SENSITIVE / suspected scorers. Offline, $0 (TF-IDF only).

- input_typicality: sweep k in {3,5,10,20} and TF-IDF backend {combined, word, char}.
- pool_disagreement_voi: partial-LOO residualizing on PEAKEDNESS ALONE vs full controls.
- headroom variants: prove the contamination IS difficulty (corr with difficulty + collapse vs clean parent).
- output_repairability: composite variants (raw nwords / structure-only / different word caps).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from scipy.sparse import hstack

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen import scorer_inputs as si
from gepa_si.screen.screen_scorers import (
    KEYS, aggregate_events, batch_frame, loro_partial, partial_spearman, screen_scorer,
)

SCORERS_PARQUET = "analysis/scorers.parquet"


def _l2(m):
    n = np.sqrt(m.multiply(m).sum(axis=1)).A1
    n[n == 0] = 1.0
    return m.multiply(1.0 / n[:, None]).tocsr()


def typicality_variants() -> pd.DataFrame:
    tr = si.trainset_meta()["inputs"]
    va = si.valset_meta()["inputs"]
    corpus = tr + va
    backends = {
        "combined": None,
        "word": TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
        "char": TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True),
    }
    out = {}  # (backend,k) -> per-trainset typicality array
    for bname, vec in backends.items():
        if bname == "combined":
            tr_m = si.embed_inputs(tr); va_m = si.valset_input_matrix()
        else:
            vec.fit(corpus)
            tr_m = _l2(vec.transform(tr)); va_m = _l2(vec.transform(va))
        sims = (tr_m @ va_m.T).toarray()  # (n_train, n_val)
        sims_sorted = np.sort(sims, axis=1)[:, ::-1]
        for k in (3, 5, 10, 20):
            out[(bname, k)] = sims_sorted[:, :k].mean(axis=1)
    return out


def main():
    runs = load_corpus()
    bf = batch_frame(runs)
    events = pd.read_parquet(SCORERS_PARQUET)
    b3keys = bf[bf.b == 3]

    # ---------- input_typicality sweep ----------
    print("=== input_typicality re-screen: k x backend (partial-LOO, b3) ===")
    typ = typicality_variants()
    rows = []
    for (bk, k), arr in typ.items():
        ev = events[["seed", "b", "iteration", "example_pos", "trainset_idx"]].copy()
        ev["typ_v"] = arr[ev["trainset_idx"].to_numpy()]
        agg = aggregate_events(ev, ["typ_v"])
        m = bf.merge(agg, on=KEYS, how="left", validate="one_to_one")
        b3 = m[m.b == 3]
        sc = screen_scorer(b3, "typ_v_mean")
        lo = loro_partial(b3, "typ_v_mean", "loo_contribution")
        rows.append({"backend": bk, "k": k, "raw_loo": sc["raw_spear_loo"],
                     "partial_loo": sc["partial_loo"], "loro_mean": lo["loro_mean"]})
    print(pd.DataFrame(rows).round(3).to_string(index=False))

    # ---------- pool_disagreement_voi: peakedness-only ----------
    print("\n=== pool_disagreement_voi: residualize on PEAKEDNESS ALONE vs full controls ===")
    agg = aggregate_events(events, ["pool_disagreement_voi"])
    m = bf.merge(agg, on=KEYS, how="left", validate="one_to_one")
    b3 = m[m.b == 3].dropna(subset=["pool_disagreement_voi_mean", "loo_contribution", "n2_peakedness"])
    x = b3["pool_disagreement_voi_mean"].to_numpy(); y = b3["loo_contribution"].to_numpy()
    print(f"  raw vs LOO:                 {partial_spearman(x, y):.3f}")
    print(f"  partial | peakedness ALONE: {partial_spearman(x, y, b3[['n2_peakedness']].to_numpy()):.3f}")
    print(f"  partial | full 4 controls:  {screen_scorer(b3, 'pool_disagreement_voi_mean')['partial_loo']:.3f}")
    print("  (peakedness IS in the 4 controls; VOI dead even isolating peakedness -> STRUCTURAL-DEAD)")

    # ---------- headroom variants: prove difficulty leakage ----------
    print("\n=== headroom variants: contamination IS difficulty ===")
    agg = aggregate_events(events, ["valset_prevalence", "prevalence_x_headroom",
                                    "input_typicality", "typicality_x_headroom"])
    m = bf.merge(agg, on=KEYS, how="left", validate="one_to_one")
    b3 = m[m.b == 3]
    for clean, hed in [("valset_prevalence", "prevalence_x_headroom"),
                       ("input_typicality", "typicality_x_headroom")]:
        sc_c = screen_scorer(b3, f"{clean}_mean"); sc_h = screen_scorer(b3, f"{hed}_mean")
        print(f"  {hed}: corr_difficulty={sc_h['corr_difficulty']:.3f}  "
              f"raw_loo={sc_h['raw_spear_loo']:.3f} -> partial_loo={sc_h['partial_loo']:.3f}  "
              f"(clean {clean} partial={sc_c['partial_loo']:.3f}; headroom made it {'WORSE' if sc_h['partial_loo']<sc_c['partial_loo'] else 'better'})")

    # ---------- output_repairability composite variants ----------
    print("\n=== output_repairability: already-screened composite + raw n_words ===")
    agg = aggregate_events(events, ["output_repairability", "output_n_words"])
    m = bf.merge(agg, on=KEYS, how="left", validate="one_to_one")
    b3 = m[m.b == 3]
    for c in ["output_repairability", "output_n_words"]:
        sc = screen_scorer(b3, f"{c}_mean"); lo = loro_partial(b3, f"{c}_mean", "loo_contribution")
        print(f"  {c}: partial_loo={sc['partial_loo']:.3f} contam_diff={sc['corr_difficulty']:.3f} "
              f"loro={lo['loro_mean']:.3f}+-{lo['loro_sd']:.3f}")


if __name__ == "__main__":
    main()
