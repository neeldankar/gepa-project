"""Offline-screen foundation + ceiling-probe scorer — read-only, no API.

Runs: build per-batch dataframe + exact ΔU (STEP 1-2), then the ceiling-probe EB scorer
evaluated leave-one-run-out vs a controls-only model (STEP 3), and emits artifacts +
the verdict (STEP 4).

    .venv/bin/python scripts/run_ceiling_probe.py
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd

from gepa_si.screen.build_batch_df import OUT_PARQUET, build_dataframe, sanity_report
from gepa_si.screen.ceiling_probe import (
    SCORER_ARTIFACT, bootstrap_ci, emit_scorer, loro,
)


def main() -> None:
    # --- STEP 1-2: dataframe + ΔU ---
    df = build_dataframe()
    os.makedirs("analysis", exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    print(f"wrote {OUT_PARQUET}: {df.shape[0]} rows x {df.shape[1]} cols\n")
    sanity_report(df)

    df_b3 = df[df.b == 3].copy()
    df_b1 = df[df.b == 1].copy()
    print(f"\nScreen set: {df_b3['seed'].nunique()} b3 runs ({len(df_b3)} batches). "
          f"Held aside: {df_b1['seed'].nunique()} b1 runs ({len(df_b1)} batches).")

    # group coverage
    n_sig = df_b3["signature"].nunique()
    n_singleton = (df_b3.groupby("signature").size() == 1).sum()
    n_ids = len({i for ids in df_b3["failed_ids"] for i in ids})
    print(f"distinct signatures (b3): {n_sig} ({n_singleton} seen once) | distinct ids: {n_ids}")

    # --- STEP 3: leave-one-run-out ---
    res = loro(df_b3)
    pd.set_option("display.width", 160, "display.max_columns", 30)
    print("\n=== leave-one-RUN-out (run = fold) ===")
    print(res.round(5).to_string(index=False))

    print("\n--- means across the 8 held-out runs ---")
    for col in ["rmse_id", "rmse_sig", "rmse_ctl", "spear_id", "spear_sig", "spear_ctl",
                "logloss_sig", "logloss_ctl", "auc_sig", "auc_ctl"]:
        print(f"  {col:12s} {np.nanmean(res[col]):.5f}")

    # --- paired per-run diffs + bootstrap CI (controls - id-family) ---
    # RMSE: lower is better -> improvement = rmse_ctl - rmse_model (positive = model better)
    # Spearman: higher is better -> improvement = spear_model - spear_ctl
    print("\n=== paired per-run differences + bootstrap 95% CI over runs (NO p-values) ===")
    comparisons = [
        ("RMSE: controls - id   (pos=id better)",   res["rmse_ctl"] - res["rmse_id"]),
        ("RMSE: controls - sig  (pos=sig better)",  res["rmse_ctl"] - res["rmse_sig"]),
        ("Spearman: id - controls (pos=id better)", res["spear_id"] - res["spear_ctl"]),
        ("Spearman: sig - controls (pos=sig better)", res["spear_sig"] - res["spear_ctl"]),
        ("AUC(accept): sig - controls (pos=sig better)", res["auc_sig"] - res["auc_ctl"]),
        ("LogLoss(accept): controls - sig (pos=sig better)", res["logloss_ctl"] - res["logloss_sig"]),
    ]
    for label, diffs in comparisons:
        m, lo, hi = bootstrap_ci(diffs.to_numpy())
        flag = "CI excludes 0" if (lo > 0 or hi < 0) else "CI spans 0"
        print(f"  {label:48s} mean={m:+.5f}  95%CI=[{lo:+.5f}, {hi:+.5f}]  ({flag})")

    # --- cross-b diagnostic: predict b1 from the b3-fit table (NOT part of the screen) ---
    from gepa_si.screen.ceiling_probe import (
        fit_id_table, fit_sig_table, predict_id, predict_sig, predict_controls, _rmse, _spear,
    )
    mu = float(df_b3["delta_u"].mean())
    id_tab, sig_tab = fit_id_table(df_b3, mu), fit_sig_table(df_b3, mu)
    if len(df_b1):
        y1 = df_b1["delta_u"].to_numpy()
        print("\n=== cross-b diagnostic (b3-fit -> predict b1; attribution only) ===")
        print(f"  sig RMSE={_rmse(predict_sig(df_b1, sig_tab, id_tab, mu), y1):.5f} "
              f"spear={_spear(predict_sig(df_b1, sig_tab, id_tab, mu), y1):.5f} | "
              f"controls RMSE={_rmse(predict_controls(df_b3, df_b1), y1):.5f} "
              f"spear={_spear(predict_controls(df_b3, df_b1), y1):.5f}")

    # --- STEP 4: emit deployable scorer (fit on all 8 b3 runs) ---
    art = emit_scorer(df_b3)
    print(f"\nwrote {SCORER_ARTIFACT}: {len(art['signature_table'])} signatures, "
          f"{len(art['id_table'])} ids, global_mean ΔU={art['global_mean_delta_u']:.5f}")
    top = sorted(art["id_table"].items(), key=lambda kv: kv[1]["shrunk"], reverse=True)[:8]
    print("top-8 ids by shrunk E[ΔU]:")
    for fid, d in top:
        print(f"  {d['shrunk']:.5f}  (n={d['n']:>3}, raw={d['raw_mean']:.5f})  {fid}")


if __name__ == "__main__":
    main()
