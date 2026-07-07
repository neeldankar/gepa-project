"""Phase-1 screening harness: partial-correlation screen of per-event scorers.

Targets (batch level): delta_u (delta_u.py) and the per-cycle LOO unique contribution
(fungibility.py) — LOO is the trustworthy one (delta_u is headroom-inflated). Per-event
scorers are aggregated to the batch (mean headline + sum secondary), then partial-Spearman'd
against each target residualizing CONTROLS. LORO over the 8 b3 runs gives stability; the
majority-tractable subset gives the live-slice read. Mirrors ceiling_probe methodology
(run = fold, bootstrap over runs, no Wald p-values).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import rankdata, spearmanr

from gepa_si.screen.build_batch_df import build_dataframe
from gepa_si.screen.ceiling_probe import CONTROLS
from gepa_si.screen.corpus_io import RunData
from gepa_si.screen.fungibility import loo_contributions
from gepa_si.screen.scorer_inputs import is_tractable_type

KEYS = ["seed", "b", "iteration"]


# ---------- per-cycle LOO target + tractable flag ----------
def batch_targets(runs: list[RunData]) -> pd.DataFrame:
    """One row per cycle: keys + loo_contribution + tractable_batch.

    LOO: accept -> loo_contributions(run)[child_idx]; reject -> 0.0 (mirrors delta_u rejects).
    tractable_batch: >50% of the batch's failed-constraint instances are tractable-type.
    """
    rows = []
    for run in runs:
        loo = loo_contributions(run)
        for c in run.cycles:
            loo_val = loo.get(c.child_idx, 0.0) if (c.accept and c.child_idx is not None) else 0.0
            flat = [f for ex in c.failed_ids_per_example for f in ex]
            n_tr = sum(is_tractable_type(f) for f in flat)
            frac_tr = (n_tr / len(flat)) if flat else 0.0
            rows.append({
                "seed": run.seed, "b": run.b, "iteration": c.iteration,
                "loo_contribution": float(loo_val),
                "frac_tractable": frac_tr,
                "tractable_batch": frac_tr > 0.5,
            })
    return pd.DataFrame(rows)


def batch_frame(runs: list[RunData]) -> pd.DataFrame:
    """build_batch_df (controls + delta_u + signature) merged with LOO target + tractable flag."""
    base = build_dataframe()  # controls, delta_u, accept, signature, failed_ids, n_failed_ids
    tgt = batch_targets(runs)
    return base.merge(tgt, on=KEYS, how="left", validate="one_to_one")


def aggregate_events(events: pd.DataFrame, scorer_cols: list[str]) -> pd.DataFrame:
    """Per-event scorer matrix -> per-batch mean (headline) and sum (secondary)."""
    g = events.groupby(KEYS, as_index=False)
    out = g[scorer_cols].mean().rename(columns={c: f"{c}_mean" for c in scorer_cols})
    s = g[scorer_cols].sum().rename(columns={c: f"{c}_sum" for c in scorer_cols})
    return out.merge(s, on=KEYS, validate="one_to_one")


# ---------- partial Spearman ----------
# Small matrix-vector / correlation ops are done off the BLAS gemm path (einsum / explicit
# sums) to avoid spurious macOS-Accelerate RuntimeWarnings on finite inputs.
def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    da, db = np.sqrt((a * a).sum()), np.sqrt((b * b).sum())
    if da == 0 or db == 0:
        return np.nan
    return float((a * b).sum() / (da * db))


def _resid_on_ranks(rv: np.ndarray, rZ: np.ndarray) -> np.ndarray:
    """Residual of ranked target rv after centered OLS on ranked controls rZ."""
    Zc = rZ - rZ.mean(axis=0)
    vc = rv - rv.mean()
    beta, *_ = np.linalg.lstsq(Zc, vc, rcond=None)
    return vc - np.einsum("ij,j->i", Zc, beta)


def partial_spearman(x, y, Z=None) -> float:
    """Spearman partial correlation: Pearson of rank-residuals of x and y on controls Z.

    Z is a 2D array (n, k) or None/empty -> ordinary Spearman. NaN-free inputs expected.
    """
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    if np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    rx, ry = rankdata(x), rankdata(y)
    if Z is None or (hasattr(Z, "shape") and Z.shape[1] == 0):
        return _pearson(rx, ry)
    Z = np.asarray(Z, float)
    rZ = np.column_stack([rankdata(Z[:, j]) for j in range(Z.shape[1])])
    ex = _resid_on_ranks(rx, rZ)
    ey = _resid_on_ranks(ry, rZ)
    if np.std(ex) == 0 or np.std(ey) == 0:
        return np.nan
    return _pearson(ex, ey)


def _spear(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    if np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    return float(spearmanr(x, y).correlation)


# ---------- per-scorer screen ----------
def screen_scorer(df: pd.DataFrame, col: str, controls=CONTROLS) -> dict:
    """Full screen of one batch-level scorer column on the given dataframe (already filtered)."""
    sub = df.dropna(subset=[col, "delta_u", "loo_contribution", *controls])
    x = sub[col].to_numpy()
    Z = sub[controls].to_numpy()
    out = {
        "n": len(sub),
        "raw_spear_du": _spear(x, sub["delta_u"]),
        "raw_spear_loo": _spear(x, sub["loo_contribution"]),
        "partial_du": partial_spearman(x, sub["delta_u"].to_numpy(), Z),
        "partial_loo": partial_spearman(x, sub["loo_contribution"].to_numpy(), Z),
    }
    for ctrl in controls:  # contamination
        out[f"corr_{ctrl}"] = _spear(x, sub[ctrl])
    return out


def loro_partial(df_b3: pd.DataFrame, col: str, target: str, controls=CONTROLS) -> dict:
    """Leave-one-run-out partial Spearman of `col` vs `target`; mean + spread over held seeds."""
    vals = []
    for held in sorted(df_b3["seed"].unique()):
        test = df_b3[df_b3.seed == held].dropna(subset=[col, target, *controls])
        if len(test) < 5:
            continue
        pc = partial_spearman(test[col].to_numpy(), test[target].to_numpy(), test[controls].to_numpy())
        if not np.isnan(pc):
            vals.append(pc)
    vals = np.array(vals, float)
    if vals.size == 0:
        return {"loro_mean": np.nan, "loro_sd": np.nan, "loro_min": np.nan, "loro_max": np.nan, "loro_n": 0}
    return {
        "loro_mean": float(vals.mean()), "loro_sd": float(vals.std()),
        "loro_min": float(vals.min()), "loro_max": float(vals.max()), "loro_n": int(vals.size),
    }


def report_rows(merged: pd.DataFrame, scorer_cols: list[str]) -> pd.DataFrame:
    """Assemble the screening table over all scorer columns (b3 pooled + tractable subset + LORO)."""
    b3 = merged[merged.b == 3]
    b3_tr = b3[b3.tractable_batch]
    rows = []
    for col in scorer_cols:
        pooled = screen_scorer(b3, col)
        tract = screen_scorer(b3_tr, col)
        loro = loro_partial(b3, col, "loo_contribution")
        rows.append({
            "scorer": col,
            "n": pooled["n"],
            "partial_loo": pooled["partial_loo"],
            "partial_du": pooled["partial_du"],
            "raw_loo": pooled["raw_spear_loo"],
            "raw_du": pooled["raw_spear_du"],
            "loro_mean": loro["loro_mean"],
            "loro_sd": loro["loro_sd"],
            "loro_min": loro["loro_min"],
            "loro_max": loro["loro_max"],
            "tract_n": tract["n"],
            "tract_partial_loo": tract["partial_loo"],
            "tract_partial_du": tract["partial_du"],
            **{f"c_{k.split('_',1)[1]}": pooled[k] for k in pooled if k.startswith("corr_")},
        })
    return pd.DataFrame(rows)
