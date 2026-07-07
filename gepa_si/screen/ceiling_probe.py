"""STEP 3 — ceiling probe: shrunk empirical-Bayes table on failed-constraint signature.

E[ΔU | group] via James–Stein / partial pooling toward the global mean:
    B_g = τ²/(τ² + σ²/n_g);  shrunk_g = μ + B_g·(m_g − μ)
with μ = batch-level global mean ΔU, σ² = pooled within-group variance, τ² = between-group
variance (method of moments). Two granularities: single failed-constraint id (attribution:
a batch feeds each of its ids) and failed-constraint signature (exact set).

Screen set = the 8 b3 runs; the 2 b1 runs are held aside (cross-b diagnostic only).
Evaluation is leave-one-RUN-out (run = fold), compared against a controls-only OLS.
No Wald p-values — paired per-run differences + bootstrap CI over runs.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

CONTROLS = ["difficulty", "n2_peakedness", "parent_dpareto", "iteration"]
SCORER_ARTIFACT = "analysis/ceiling_probe_scorer.json"
RNG = np.random.default_rng(0)
N_BOOT = 2000


# ---------- empirical-Bayes shrinkage ----------
def eb_shrink(values_by_group: dict[str, list[float]], mu: float) -> dict[str, dict]:
    """Return {group: {n, raw_mean, shrunk}} via James–Stein partial pooling toward mu."""
    groups = {g: np.asarray(v, dtype=float) for g, v in values_by_group.items() if len(v) > 0}
    means = {g: float(v.mean()) for g, v in groups.items()}
    ns = {g: int(v.size) for g, v in groups.items()}

    # pooled within-group variance (groups with n>=2 contribute)
    num = sum(float(((v - v.mean()) ** 2).sum()) for v in groups.values() if v.size >= 2)
    den = sum((v.size - 1) for v in groups.values() if v.size >= 2)
    sigma2 = (num / den) if den > 0 else 0.0

    # between-group variance (MoM): Var(group means) - mean(sigma2/n_g)
    m_arr = np.array(list(means.values()))
    var_means = float(m_arr.var()) if m_arr.size > 1 else 0.0
    mean_se = float(np.mean([sigma2 / ns[g] for g in groups])) if groups else 0.0
    tau2 = max(0.0, var_means - mean_se)

    out = {}
    for g in groups:
        if tau2 <= 0.0:
            B = 0.0  # no between-group signal -> fully pool to mu
        elif sigma2 <= 0.0:
            B = 1.0  # no within-group noise -> trust the group mean
        else:
            B = tau2 / (tau2 + sigma2 / ns[g])
        out[g] = {"n": ns[g], "raw_mean": means[g], "shrunk": mu + B * (means[g] - mu)}
    return out


def _explode_ids(df: pd.DataFrame) -> dict[str, list[float]]:
    vals: dict[str, list[float]] = {}
    for ids, du in zip(df["failed_ids"], df["delta_u"]):
        for fid in ids:
            vals.setdefault(fid, []).append(float(du))
    return vals


def fit_id_table(df: pd.DataFrame, mu: float) -> dict[str, dict]:
    return eb_shrink(_explode_ids(df), mu)


def fit_sig_table(df: pd.DataFrame, mu: float) -> dict[str, dict]:
    vals: dict[str, list[float]] = {}
    for sig, du in zip(df["signature"], df["delta_u"]):
        vals.setdefault(sig, []).append(float(du))
    return eb_shrink(vals, mu)


# ---------- predictors (with backoff to global mean) ----------
def predict_id(df: pd.DataFrame, id_table: dict, mu: float) -> np.ndarray:
    preds = []
    for ids in df["failed_ids"]:
        vals = [id_table[f]["shrunk"] for f in ids if f in id_table]
        preds.append(float(np.mean(vals)) if vals else mu)  # mean over batch's ids; unseen->mu
    return np.array(preds)


def predict_sig(df: pd.DataFrame, sig_table: dict, id_table: dict, mu: float) -> np.ndarray:
    preds = []
    for sig, ids in zip(df["signature"], df["failed_ids"]):
        if sig in sig_table:
            preds.append(sig_table[sig]["shrunk"])
        else:  # back off: id-level mean -> global mean
            vals = [id_table[f]["shrunk"] for f in ids if f in id_table]
            preds.append(float(np.mean(vals)) if vals else mu)
    return np.array(preds)


def predict_controls(train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
    lr = make_pipeline(StandardScaler(), LinearRegression())
    lr.fit(train[CONTROLS].to_numpy(), train["delta_u"].to_numpy())
    return np.clip(lr.predict(test[CONTROLS].to_numpy()), 0.0, None)  # ΔU >= 0


# ---------- metrics ----------
def _rmse(p, y):
    return float(np.sqrt(np.mean((np.asarray(p) - np.asarray(y)) ** 2)))


def _spear(p, y):
    if np.std(p) == 0 or np.std(y) == 0:
        return np.nan
    return float(spearmanr(p, y).correlation)


# ---------- leave-one-run-out ----------
def loro(df_b3: pd.DataFrame) -> pd.DataFrame:
    seeds = sorted(df_b3["seed"].unique())
    rows = []
    for held in seeds:
        train = df_b3[df_b3.seed != held]
        test = df_b3[df_b3.seed == held]
        mu = float(train["delta_u"].mean())
        id_tab = fit_id_table(train, mu)
        sig_tab = fit_sig_table(train, mu)

        y = test["delta_u"].to_numpy()
        p_id = predict_id(test, id_tab, mu)
        p_sig = predict_sig(test, sig_tab, id_tab, mu)
        p_ctl = predict_controls(train, test)

        # secondary: accept (EB on accept-rate per signature vs controls logistic)
        acc = test["accept"].astype(int).to_numpy()
        acc_mu = float(train["accept"].mean())
        acc_sig = eb_shrink(
            {s: g["accept"].astype(float).tolist() for s, g in train.groupby("signature")}, acc_mu
        )
        p_acc_sig = np.array([acc_sig[s]["shrunk"] if s in acc_sig else acc_mu for s in test["signature"]])
        p_acc_sig = np.clip(p_acc_sig, 1e-6, 1 - 1e-6)
        clf = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
        clf.fit(train[CONTROLS], train["accept"].astype(int))
        p_acc_ctl = np.clip(clf.predict_proba(test[CONTROLS])[:, 1], 1e-6, 1 - 1e-6)

        def safe_auc(yy, pp):
            return float(roc_auc_score(yy, pp)) if len(set(yy)) > 1 and np.std(pp) > 0 else np.nan

        rows.append({
            "held_seed": held, "n_test": len(test),
            "rmse_id": _rmse(p_id, y), "rmse_sig": _rmse(p_sig, y), "rmse_ctl": _rmse(p_ctl, y),
            "spear_id": _spear(p_id, y), "spear_sig": _spear(p_sig, y), "spear_ctl": _spear(p_ctl, y),
            "logloss_sig": float(log_loss(acc, p_acc_sig, labels=[0, 1])),
            "logloss_ctl": float(log_loss(acc, p_acc_ctl, labels=[0, 1])),
            "auc_sig": safe_auc(acc, p_acc_sig), "auc_ctl": safe_auc(acc, p_acc_ctl),
        })
    return pd.DataFrame(rows)


def bootstrap_ci(per_run_diffs: np.ndarray, n_boot: int = N_BOOT) -> tuple[float, float, float]:
    """Mean paired diff + 95% percentile CI by resampling runs (no p-values)."""
    d = np.asarray(per_run_diffs, dtype=float)
    d = d[~np.isnan(d)]
    boots = [RNG.choice(d, size=d.size, replace=True).mean() for _ in range(n_boot)]
    return float(d.mean()), float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def emit_scorer(df_b3: pd.DataFrame, path: str = SCORER_ARTIFACT) -> dict:
    """Fit on ALL 8 b3 runs and save the deployable shrunk tables."""
    mu = float(df_b3["delta_u"].mean())
    artifact = {
        "global_mean_delta_u": mu,
        "n_batches": int(len(df_b3)),
        "id_table": fit_id_table(df_b3, mu),
        "signature_table": fit_sig_table(df_b3, mu),
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)
    return artifact
