"""WAVE 2 — reconstruction-gated scorers: build, screen, report. Offline, $0.

Run: HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/run_scorers_wave2.py
(Requires Wave 1 to have written analysis/scorers.parquet.)
"""

from __future__ import annotations

import os

import pandas as pd

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.scorers import SCORERS_PARQUET, EVENT_KEYS
from gepa_si.screen.scorers_wave2 import WAVE2_COLS, build_wave2_matrix
from gepa_si.screen.screen_scorers import (
    KEYS, aggregate_events, batch_frame, partial_spearman, report_rows,
)

pd.set_option("display.width", 200, "display.max_columns", 40)


def main():
    runs = load_corpus()
    print(f"loaded {len(runs)} runs")

    ev2, diag = build_wave2_matrix(runs)
    print("\n=== Wave 2 build diagnostics ===")
    print(f"  events: {diag['n_events']}")
    print(f"  coverage-gap: fraction of failed constraints classified ABSENT (no rule in prompt): "
          f"{diag['absent_frac_of_failed']:.3f}")
    print(f"  seed-to-parent: fraction of events with ANY seed-evaluated failed constraint "
          f"(#9 coverage): {diag['seed_coverage_frac']:.3f}")
    if diag["seed_coverage_frac"] < 0.05:
        print("  ! seed coverage < 5% -> #9 is too sparse to screen meaningfully; reporting as such.")

    # merge wave2 per-event cols into the persisted scorer matrix
    ev1 = pd.read_parquet(SCORERS_PARQUET)
    events = ev1.merge(ev2, on=EVENT_KEYS, how="left", validate="one_to_one")

    bf = batch_frame(runs)
    agg = aggregate_events(events, WAVE2_COLS)
    merged = bf.merge(agg, on=KEYS, how="left", validate="one_to_one")

    cols = [f"{c}_mean" for c in WAVE2_COLS]
    table = report_rows(merged, cols).sort_values("partial_loo", key=lambda s: s.abs(), ascending=False)

    show = ["scorer", "n", "partial_loo", "partial_du", "raw_loo", "raw_du",
            "loro_mean", "loro_sd", "loro_min", "loro_max",
            "tract_n", "tract_partial_loo", "tract_partial_du"]
    print("\n=== WAVE 2 screen — MEAN agg (b3 pooled; partial = resid on 4 controls incl. iteration) ===")
    print(table[show].round(3).to_string(index=False))

    print("\n=== contamination (scorer Spearman vs each control) ===")
    cc = ["scorer", "c_difficulty", "c_n2_peakedness", "c_parent_dpareto", "c_iteration"]
    print(table[cc].round(3).to_string(index=False))

    # LEAD scorer #8: explicit iteration-only residualization (brief mandate)
    b3 = merged[merged.b == 3].dropna(subset=["coverage_gap_mean", "loo_contribution", "iteration"])
    x = b3["coverage_gap_mean"].to_numpy()
    it = b3[["iteration"]].to_numpy()
    print("\n=== coverage_gap: iteration channel check ===")
    print(f"  raw Spearman vs LOO:                 {partial_spearman(x, b3['loo_contribution'].to_numpy()):.3f}")
    print(f"  partial vs LOO | iteration ONLY:     {partial_spearman(x, b3['loo_contribution'].to_numpy(), it):.3f}")
    print(f"  partial vs LOO | all 4 controls:     {table.loc[table.scorer=='coverage_gap_mean','partial_loo'].iloc[0]:.3f}")
    print(f"  (corr with iteration = {table.loc[table.scorer=='coverage_gap_mean','c_iteration'].iloc[0]:.3f}; "
          "if signal dies after residualizing iteration, it was iteration-in-disguise)")

    os.makedirs("analysis", exist_ok=True)
    events.to_parquet(SCORERS_PARQUET, index=False)
    print(f"\nwrote {SCORERS_PARQUET}: {events.shape[0]} events x {events.shape[1]} cols (waves 1+2)")


if __name__ == "__main__":
    main()
