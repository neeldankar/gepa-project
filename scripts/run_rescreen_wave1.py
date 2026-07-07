"""WAVE 1 re-screen — reopened SEMANTIC scorers on the CORRECT reflection object.

Screening level only (LORO ranking + residualization). NO permutation-MAX null / M-variant
hardening — that is Wave 2, gated on a survivor existing here.

For each reopened semantic scorer (knn_novelty, ncd_novelty, actionability, nov_x_act) we
report three computations — (a) Feedback-string only, (b) full triple, (c) delta b-a — each
screened three ways against the batch-level LOO unique-contribution target:
  - raw_loo     : Spearman, no controls
  - partial_loo : residualized on the 4 difficulty controls (prior-comparable)
  - constid_loo : residualized on 4 controls + constraint_tractability + multi-hot failed-type
                  composition  (the SURVIVAL test: does it add signal BEYOND constraint identity?)
Plus the [new] output failure-MODE signature, and the [stays-dead-confirm] id-keyed
failure-signature singleton ceiling.

Run: HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/run_rescreen_wave1.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gepa_si.screen.ceiling_probe import CONTROLS
from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.scorer_inputs import constraint_type
from gepa_si.screen.scorers import SCORERS_PARQUET
from gepa_si.screen.scorers_semantic import (
    SEMANTIC_BASES, SEMANTIC_COLS, build_semantic_matrix,
)
from gepa_si.screen.screen_scorers import (
    KEYS, aggregate_events, batch_frame, loro_partial, partial_spearman,
)
from scipy.stats import spearmanr

pd.set_option("display.width", 240, "display.max_columns", 50)

OUT_PARQUET = "analysis/rescreen_wave1.parquet"
MIN_TYPE_BATCHES = 5   # drop failed-type-composition controls present in <5 b3 batches


def _spear(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    return float(spearmanr(x, y).correlation)


def build_merged():
    """batch_frame + semantic batch-means + constraint_tractability_mean + type-composition."""
    runs = load_corpus()
    sem = build_semantic_matrix(runs)
    agg_sem = aggregate_events(sem, SEMANTIC_COLS)

    ev = pd.read_parquet(SCORERS_PARQUET)                 # existing per-event waves 1+2+3
    agg_ct = aggregate_events(ev, ["constraint_tractability"])[KEYS + ["constraint_tractability_mean"]]

    bf = batch_frame(runs)
    merged = bf.merge(agg_sem, on=KEYS, how="left", validate="one_to_one") \
               .merge(agg_ct, on=KEYS, how="left", validate="one_to_one")

    # multi-hot failed-type composition (fraction of the batch's failed-id instances per type)
    all_types = sorted({constraint_type(f) for ids in merged["failed_ids"] for f in ids})
    for t in all_types:
        merged[f"ct_{t}"] = merged["failed_ids"].apply(
            lambda ids: (sum(constraint_type(f) == t for f in ids) / len(ids)) if ids else 0.0
        )
    b3 = merged[merged.b == 3]
    type_cols = [f"ct_{t}" for t in all_types if int((b3[f"ct_{t}"] > 0).sum()) >= MIN_TYPE_BATCHES]
    return merged, type_cols


def screen_col(b3: pd.DataFrame, col: str, constid_controls) -> dict:
    sub = b3.dropna(subset=[col, "loo_contribution", *CONTROLS, *constid_controls])
    x = sub[col].to_numpy()
    loo = sub["loo_contribution"].to_numpy()
    raw = _spear(x, loo)
    partial = partial_spearman(x, loo, sub[CONTROLS].to_numpy())
    constid = partial_spearman(x, loo, sub[constid_controls].to_numpy())
    lc = loro_partial(b3, col, "loo_contribution", controls=constid_controls)
    return {"n": len(sub), "raw_loo": raw, "partial_loo": partial,
            "constid_loo": constid, "loro_constid_mean": lc["loro_mean"], "loro_constid_sd": lc["loro_sd"]}


def main():
    merged, type_cols = build_merged()
    constid_controls = list(CONTROLS) + ["constraint_tractability_mean"] + type_cols
    b3 = merged[merged.b == 3].copy()
    print(f"b3 batches: {len(b3)}  | constraint-id controls: 4 difficulty + tractability + "
          f"{len(type_cols)} failed-type-composition columns")

    # ---------------- (a)/(b)/(c) three-way table for the four semantic scorers ----------------
    rows = []
    for base in SEMANTIC_BASES:
        for variant in ("a", "b", "delta"):
            col = f"{base}_{variant}_mean"
            r = screen_col(b3, col, constid_controls)
            rows.append({"base": base, "variant": variant, **r})
    # failure-mode (single, output-derived)
    rows.append({"base": "failure_mode", "variant": "b", **screen_col(b3, "failure_mode_mean", constid_controls)})
    tab = pd.DataFrame(rows)

    print("\n" + "=" * 110)
    print("THREE-WAY SCREEN — (a) feedback-string | (b) full triple | delta(b-a)   vs batch LOO contribution")
    print("=" * 110)
    show = ["base", "variant", "n", "raw_loo", "partial_loo", "constid_loo", "loro_constid_mean", "loro_constid_sd"]
    print(tab[show].round(4).to_string(index=False))

    # metric deltas (b - a) on each screen axis -> "what the output/input added"
    print("\n--- metric delta (b - a): the signal added by the Output/Input ---")
    piv = tab[tab.variant.isin(["a", "b"])].pivot(index="base", columns="variant",
                                                  values=["raw_loo", "partial_loo", "constid_loo"])
    for base in SEMANTIC_BASES:
        d_raw = piv.loc[base, ("raw_loo", "b")] - piv.loc[base, ("raw_loo", "a")]
        d_par = piv.loc[base, ("partial_loo", "b")] - piv.loc[base, ("partial_loo", "a")]
        d_cid = piv.loc[base, ("constid_loo", "b")] - piv.loc[base, ("constid_loo", "a")]
        print(f"  {base:14}  Δraw={d_raw:+.4f}  Δpartial={d_par:+.4f}  Δconstid={d_cid:+.4f}")

    # ---------------- [stays-dead-confirm] failure-signature singleton ceiling ----------------
    sig = b3["signature"]
    n_batch = len(sig)
    vc = sig.value_counts()
    n_unique = int(vc.size)
    n_singleton = int((vc == 1).sum())
    nonempty = b3[b3["n_failed_ids"] > 0]["signature"]
    print("\n" + "-" * 110)
    print("[stays-dead-confirm] id-keyed failure-signature on the new object:")
    print(f"  b3 batches={n_batch}  distinct signatures={n_unique}  singletons={n_singleton} "
          f"({100*n_singleton/n_batch:.1f}%)  | nonempty-failure batches={len(nonempty)}")
    print(f"  -> still ceilinged (singletons dominate): {'YES, stays dead' if n_singleton/n_batch > 0.85 else 'NO'}")

    # ---------------- verdict ----------------
    # A reopened semantic scorer SURVIVES Wave-1 triage only if, on the full object (b):
    #   (1) it adds signal beyond constraint identity:        constid_loo(b) > 0.05
    #   (2) that signal is OUTPUT-origin (the reopening premise): constid_loo(b) - constid_loo(a) > 0
    #   (3) it is LORO-stable:                                 loro_constid_mean - loro_constid_sd > 0
    # (1) alone is variance, not usefulness; (2) is the whole point of re-screening on the
    # real object — if the gain isn't from the Output it predates the correction.
    print("\n" + "=" * 110)
    a_constid = {b: float(tab[(tab.base == b) & (tab.variant == "a")]["constid_loo"].iloc[0])
                 for b in SEMANTIC_BASES}
    survivors = []
    for _, r in tab[tab.variant == "b"].iterrows():
        c_a = a_constid.get(r["base"], 0.0)
        c1 = r["constid_loo"] > 0.05
        c2 = (r["constid_loo"] - c_a) > 0
        c3 = (r["loro_constid_mean"] - r["loro_constid_sd"]) > 0
        flag = "SURVIVES" if (c1 and c2 and c3) else "dead"
        print(f"  {r['base']:14} constid_b={r['constid_loo']:+.4f}  "
              f"Δconstid(b-a)={r['constid_loo']-c_a:+.4f}  "
              f"LORO={r['loro_constid_mean']:+.3f}±{r['loro_constid_sd']:.3f}  "
              f"[beyond-id={c1} output-origin={c2} stable={c3}] -> {flag}")
        if c1 and c2 and c3:
            survivors.append(r["base"])
    print("\nSURVIVORS:", survivors if survivors else "NONE — null holds on the correct object")
    print("=" * 110)

    tab.round(5).to_parquet(OUT_PARQUET, index=False)
    print(f"\nwrote {OUT_PARQUET}")
    return tab


if __name__ == "__main__":
    main()
