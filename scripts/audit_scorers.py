"""Phase 1.5 — adversarial post-mortem of every FAILED Phase-1 scorer. Offline, $0.

Reads analysis/scorers.parquet + the baseline corpus. NEVER touches logs/phase2/.
Produces: per-scorer construction printouts, variance/degeneracy, raw-vs-partial Spearman vs LOO,
control contamination, a category per scorer, conditional re-screens, and the deliverables
analysis/scorer_audit.parquet + analysis/scorer_audit.md.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.scorer_inputs import (
    classify_coverage, constraint_type, reconstruct_prompts, valset_meta, _strip,
)
from gepa_si.screen.screen_scorers import (
    KEYS, aggregate_events, batch_frame, loro_partial, screen_scorer,
)
from gepa_si.screen.ceiling_probe import CONTROLS

SCORERS_PARQUET = "analysis/scorers.parquet"

FAILED = [
    "valset_prevalence", "input_typicality", "prevalence_x_headroom", "typicality_x_headroom",
    "parent_near_frontier", "pool_disagreement_voi", "coverage_gap", "coverage_gap_x_prevalence",
    "seed_to_parent_regression", "output_repairability", "output_n_words",
]

# Phase-1 literal construction (for the post-mortem "exact construction" field).
CONSTRUCTION = {
    "valset_prevalence": "Σ_{c∈failed(e)} prevalence_valset(c)",
    "input_typicality": "mean cosine (word+char TF-IDF) of e.input to its 5 nearest valset inputs",
    "prevalence_x_headroom": "Σ_{c∈failed(e)} Σ_{val i ∋ c} (1 − pool_best_i)",
    "typicality_x_headroom": "Σ over 5 nearest valset neighbors of sim_i·(1 − pool_best_i)",
    "parent_near_frontier": "Σ_{c∈failed} Σ_i w_i·1[c∈val_i], w=1[B<1]·clip(1−(B−p),0,1)",
    "pool_disagreement_voi": "mean over e's 5 nearest valset cells of Var across pool candidates",
    "coverage_gap": "Σ_{c∈failed} (1.0 if ABSENT else 0.25) via classify_coverage keyword matcher",
    "coverage_gap_x_prevalence": "Σ_{c∈failed, ABSENT} prevalence_valset(c)",
    "seed_to_parent_regression": "count of c the SEED passed on example j but the PARENT now fails",
    "output_repairability": "min(1,nwords/120)·(.5+.5·structure)·(.5+.5·complete)",
    "output_n_words": "log1p(word count of parent output)",
}


def variance_summary(v: np.ndarray) -> dict:
    vd = v[~np.isnan(v)]
    if len(vd) == 0:
        return dict(n=0, frac_zero=np.nan, mode_frac=np.nan, n_distinct=0,
                    vmin=np.nan, vmed=np.nan, vmax=np.nan)
    r = np.round(vd, 6)
    mode_frac = pd.Series(r).value_counts(normalize=True).iloc[0]
    return dict(n=len(vd), frac_zero=float((vd == 0).mean()), mode_frac=float(mode_frac),
                n_distinct=int(len(np.unique(r))), vmin=float(vd.min()),
                vmed=float(np.median(vd)), vmax=float(vd.max()))


def per_event_index(runs):
    """(seed,b,iteration,example_pos) -> {failed, trainset_idx, parent_id, seed}."""
    idx = {}
    for run in runs:
        for c in run.cycles:
            for p, failed in enumerate(c.failed_ids_per_example):
                idx[(run.seed, run.b, c.iteration, p)] = {
                    "failed": failed, "trainset_idx": c.minibatch_ids[p], "parent_id": c.parent_id,
                }
    return idx


def main():
    runs = load_corpus()
    events = pd.read_parquet(SCORERS_PARQUET)
    bf = batch_frame(runs)
    agg = aggregate_events(events, FAILED)
    merged = bf.merge(agg, on=KEYS, how="left", validate="one_to_one")
    b3 = merged[merged.b == 3]

    print("=== PER-SCORER STATS (b3 pooled, mean agg; LOO = trustworthy target) ===")
    rows = []
    for s in FAILED:
        col = f"{s}_mean"
        sc = screen_scorer(b3, col)
        ev_var = variance_summary(events[s].to_numpy())
        bt_var = variance_summary(b3[col].to_numpy())
        contam = max(abs(sc[f"corr_{c}"]) for c in CONTROLS)
        drop = abs(sc["raw_spear_loo"]) - abs(sc["partial_loo"])
        rows.append({
            "scorer": s, "raw_loo": sc["raw_spear_loo"], "partial_loo": sc["partial_loo"],
            "drop": drop, "contam_max": contam, "contam_difficulty": sc["corr_difficulty"],
            "ev_frac_zero": ev_var["frac_zero"], "ev_mode_frac": ev_var["mode_frac"],
            "bt_n_distinct": bt_var["n_distinct"], "bt_mode_frac": bt_var["mode_frac"],
        })
    tab = pd.DataFrame(rows)
    print(tab.round(3).to_string(index=False))

    # ---- 5 example events per scorer (inspectable construction) ----
    idx = per_event_index(runs)
    prompts_cache = {}

    def parent_prompt(seed, b, parent_id):
        key = (seed, b)
        if key not in prompts_cache:
            run = next(r for r in runs if r.seed == seed and r.b == b)
            prompts_cache[key] = reconstruct_prompts(run.log_path)
        return prompts_cache[key].get(parent_id, "")

    print("\n=== EXAMPLE EVENTS (5 each; inputs -> output) ===")
    ev_b3 = events[events.b == 3].reset_index(drop=True)
    rng = np.random.default_rng(0)
    for s in FAILED:
        print(f"\n--- {s}  [{CONSTRUCTION[s]}] ---")
        # prefer non-degenerate rows so the computation is visible
        nz = ev_b3[ev_b3[s] != 0]
        pick = nz if len(nz) >= 5 else ev_b3
        sample = pick.iloc[rng.choice(len(pick), size=min(5, len(pick)), replace=False)]
        for _, r in sample.iterrows():
            meta = idx.get((r.seed, r.b, r.iteration, r.example_pos), {})
            failed = meta.get("failed", [])
            print(f"  seed{r.seed} it{r.iteration} pos{r.example_pos} "
                  f"failed={failed} -> {s}={r[s]:.4f}")

    tab.to_parquet("analysis/scorer_audit_stats.parquet", index=False)
    print("\nwrote analysis/scorer_audit_stats.parquet")


if __name__ == "__main__":
    main()
