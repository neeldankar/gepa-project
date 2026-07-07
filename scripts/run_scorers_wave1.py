"""WAVE 1 — computable-now scorers: build, screen, report. Offline, $0, read-only on logs/.

Run: HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/run_scorers_wave1.py
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.fungibility import loo_contributions
from gepa_si.screen.scorers import build_event_matrix, WAVE1_COLS, SCORERS_PARQUET
from gepa_si.screen.screen_scorers import (
    KEYS, aggregate_events, batch_frame, partial_spearman, report_rows,
)

pd.set_option("display.width", 200, "display.max_columns", 40)


def self_checks(runs, events, merged):
    print("=== self-checks ===")
    # (b) event->trainset join already verified in scorer_inputs (0 misses); reconfirm count
    print(f"  events: {len(events)}  (expect 1251)")
    # (a) per-cycle LOO target sums ~ sum of accepted-child LOO contributions per run
    ok = True
    for run in runs:
        loo = loo_contributions(run)
        accepted_sum = sum(v for k, v in loo.items() if k != 0)
        m = merged[(merged.seed == run.seed) & (merged.b == run.b)]
        cyc_sum = m["loo_contribution"].sum()
        if abs(accepted_sum - cyc_sum) > 1e-6:
            ok = False
            print(f"  ! seed{run.seed}_b{run.b}: cycle LOO sum {cyc_sum:.5f} != accepted LOO {accepted_sum:.5f}")
    print(f"  LOO target reconciles per run: {ok}")
    # (c) partial_spearman recovers raw Spearman when Z empty
    rng = np.random.default_rng(0)
    a, bb = rng.normal(size=200), rng.normal(size=200)
    from scipy.stats import spearmanr
    d = abs(partial_spearman(a, bb, np.empty((200, 0))) - spearmanr(a, bb).correlation)
    print(f"  partial_spearman==Spearman with empty Z: {d < 1e-9} (diff={d:.2e})")
    # tractable subset size
    b3 = merged[merged.b == 3]
    print(f"  b3 batches: {len(b3)}  tractable-subset: {int(b3.tractable_batch.sum())} "
          f"({100*b3.tractable_batch.mean():.1f}%)")


def main():
    runs = load_corpus()
    print(f"loaded {len(runs)} runs")

    events = build_event_matrix(runs)
    bf = batch_frame(runs)
    agg = aggregate_events(events, WAVE1_COLS)
    merged = bf.merge(agg, on=KEYS, how="left", validate="one_to_one")

    self_checks(runs, events, merged)

    # screen the mean-aggregated columns (headline) and sum-aggregated columns (secondary)
    mean_cols = [f"{c}_mean" for c in WAVE1_COLS]
    sum_cols = [f"{c}_sum" for c in WAVE1_COLS]
    table = report_rows(merged, mean_cols).sort_values("partial_loo", key=lambda s: s.abs(), ascending=False)
    table_sum = report_rows(merged, sum_cols).sort_values("partial_loo", key=lambda s: s.abs(), ascending=False)

    show = ["scorer", "n", "partial_loo", "partial_du", "raw_loo", "raw_du",
            "loro_mean", "loro_sd", "loro_min", "loro_max",
            "tract_n", "tract_partial_loo", "tract_partial_du"]
    print("\n=== WAVE 1 screen — MEAN agg (headline; b3 pooled; partial = resid on 4 controls) ===")
    print(table[show].round(3).to_string(index=False))
    print("\n=== WAVE 1 screen — SUM agg (secondary) ===")
    print(table_sum[["scorer", "partial_loo", "partial_du", "loro_mean", "loro_sd"]].round(3).to_string(index=False))

    print("\n=== contamination — MEAN agg (scorer Spearman vs each control) ===")
    cc = ["scorer", "c_difficulty", "c_n2_peakedness", "c_parent_dpareto", "c_iteration"]
    print(table[cc].round(3).to_string(index=False))

    # persist per-event matrix
    os.makedirs("analysis", exist_ok=True)
    events.to_parquet(SCORERS_PARQUET, index=False)
    print(f"\nwrote {SCORERS_PARQUET}: {events.shape[0]} events x {events.shape[1]} cols")


if __name__ == "__main__":
    main()
