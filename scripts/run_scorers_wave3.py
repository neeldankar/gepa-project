"""WAVE 3 — output-pathology (#11) build + screen, then the FINAL ranked deliverable across
all built scorers. Offline, $0. Requires Waves 1-2 to have written analysis/scorers.parquet.

Run: HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/run_scorers_wave3.py
"""

from __future__ import annotations

import os

import pandas as pd

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.scorers import SCORERS_PARQUET, EVENT_KEYS, WAVE1_COLS
from gepa_si.screen.scorers_wave2 import WAVE2_COLS
from gepa_si.screen.scorers_wave3 import WAVE3_COLS, build_wave3_matrix
from gepa_si.screen.screen_scorers import KEYS, aggregate_events, batch_frame, report_rows

pd.set_option("display.width", 220, "display.max_columns", 40)

# scorers too sparse / contaminated to rank as survivors (reported, not recommended)
SPARSE = {"seed_to_parent_regression"}


def main():
    runs = load_corpus()
    print(f"loaded {len(runs)} runs")

    ev3 = build_wave3_matrix(runs)
    ev = pd.read_parquet(SCORERS_PARQUET)                       # waves 1+2
    events = ev.merge(ev3, on=EVENT_KEYS, how="left", validate="one_to_one")

    bf = batch_frame(runs)
    all_cols = WAVE1_COLS + WAVE2_COLS + WAVE3_COLS
    agg = aggregate_events(events, all_cols)
    merged = bf.merge(agg, on=KEYS, how="left", validate="one_to_one")

    cols = [f"{c}_mean" for c in WAVE3_COLS]
    w3 = report_rows(merged, cols)
    print("\n=== WAVE 3 screen — output-pathology (#11) ===")
    show = ["scorer", "n", "partial_loo", "partial_du", "raw_loo", "loro_mean", "loro_sd"]
    print(w3[show].round(3).to_string(index=False))

    # ---- FINAL ranked deliverable across every built scorer ----
    final = report_rows(merged, [f"{c}_mean" for c in all_cols])
    final["base"] = final["scorer"].str.replace("_mean", "", regex=False)
    final["status"] = final["base"].apply(lambda b: "SPARSE/NR" if b in SPARSE else "screened")
    final = final.sort_values("partial_loo", key=lambda s: s.abs(), ascending=False)

    print("\n" + "=" * 100)
    print("FINAL RANKED TABLE — partial Spearman vs LOO-contribution (b3 pooled), trustworthy target")
    print("=" * 100)
    show = ["scorer", "status", "n", "partial_loo", "partial_du", "loro_mean", "loro_sd",
            "tract_n", "tract_partial_loo", "c_difficulty", "c_iteration"]
    print(final[show].round(3).to_string(index=False))

    os.makedirs("analysis", exist_ok=True)
    events.to_parquet(SCORERS_PARQUET, index=False)
    print(f"\nwrote {SCORERS_PARQUET}: {events.shape[0]} events x {events.shape[1]} cols (waves 1+2+3)")
    final.round(4).to_parquet("analysis/scorer_ranking.parquet", index=False)
    print("wrote analysis/scorer_ranking.parquet (the final ranked table)")


if __name__ == "__main__":
    main()
