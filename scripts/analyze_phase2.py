"""Phase-2 locked analysis: paired tractability vs uniform on OOD test U.

Reads logs/phase2/*.oodtest.json (no API), pairs per seed, runs the pre-registered test:
sign-flip permutation (exact, 2^n) on paired differences + bootstrap CI over seeds. Applies
the pre-committed decision rule. Writes analysis/phase2_results.parquet.

Run: .venv/bin/python scripts/analyze_phase2.py
"""

from __future__ import annotations

import glob
import itertools
import json
import os

import numpy as np
import pandas as pd

LOG_DIR = "logs/phase2"
OUT = "analysis/phase2_results.parquet"
N_BOOT = 10000
RNG = np.random.default_rng(0)


def _load() -> pd.DataFrame:
    rows = []
    for path in glob.glob(f"{LOG_DIR}/*.oodtest.json"):
        r = json.load(open(path, encoding="utf-8"))
        rows.append({"seed": r["seed"], "arm": r["arm"], "test_U": r["test_U"],
                     "n_test": r["n_test"], "stem": r["stem"]})
    return pd.DataFrame(rows)


def sign_flip_p(diffs: np.ndarray) -> float:
    """Exact two-sided sign-flip permutation p on paired differences."""
    n = len(diffs)
    obs = abs(diffs.mean())
    count = 0
    for signs in itertools.product([1, -1], repeat=n):
        if abs((diffs * np.array(signs)).mean()) >= obs - 1e-12:
            count += 1
    return count / (2 ** n)


def bootstrap_ci(diffs: np.ndarray) -> tuple[float, float]:
    boots = [RNG.choice(diffs, size=len(diffs), replace=True).mean() for _ in range(N_BOOT)]
    return float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))


def main():
    df = _load()
    if df.empty:
        print("no oodtest.json files yet under logs/phase2/")
        return
    wide = df.pivot_table(index="seed", columns="arm", values="test_U")
    paired = wide.dropna(subset=["uniform", "tractability"]).copy()
    paired["diff"] = paired["tractability"] - paired["uniform"]

    print("=== Phase-2 per-seed OOD test U ===")
    print(paired.round(4).to_string())
    diffs = paired["diff"].to_numpy()
    n = len(diffs)
    print(f"\npaired seeds: {n}")
    if n == 0:
        return
    mean_d = float(diffs.mean())
    lo, hi = bootstrap_ci(diffs) if n >= 2 else (float("nan"), float("nan"))
    p = sign_flip_p(diffs)

    print(f"mean paired diff (tractability - uniform): {mean_d:+.4f}")
    print(f"bootstrap 95% CI over seeds: [{lo:+.4f}, {hi:+.4f}]")
    print(f"sign-flip permutation p (two-sided, exact): {p:.4f}")

    print("\n=== DECISION RULE ===")
    if n < 6:
        verdict = f"INSUFFICIENT N ({n} < 6 pairs) — not yet decisive per prereg."
    elif mean_d > 0 and lo > 0:
        verdict = "SCOPED WIN: positive mean diff, bootstrap CI excludes 0."
    elif mean_d < 0 and hi < 0:
        verdict = "REVERSE EFFECT: tractability significantly WORSE than uniform."
    else:
        verdict = ("NULL: CI spans 0 — difficulty hard to beat on verifiable IF; "
                   "offline screen stands as the supporting evidence.")
    print(verdict)

    os.makedirs("analysis", exist_ok=True)
    paired.reset_index().to_parquet(OUT, index=False)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
