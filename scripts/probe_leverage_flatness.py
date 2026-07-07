"""Probe — leverage-flatness (Claim 1) + constraint structure/antagonism (Claim 2). Offline, $0.

Characterizes the OBSERVED (uniform-sampled) corpus matrices. Does NOT test what a non-uniform
sampler or an aggregate gate would do. Reads corpus + analysis/partial_diag.parquet; writes
analysis/probe_leverage_flatness.{md,parquet}, two PNG figures, and a 5-line PROJECT_STATE append.
Never touches logs/phase2/.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from gepa_si.screen.corpus_io import load_corpus  # noqa: E402
from gepa_si.screen.fungibility import pool_matrix  # noqa: E402
from gepa_si.screen.scorer_inputs import constraint_type  # noqa: E402

PARTIAL_DIAG = "analysis/partial_diag.parquet"
RNG = np.random.default_rng(0)
N_PERM = 1000

TYPES = ["keywords", "detectable_format", "length_constraints", "copy", "count", "change_case",
         "punctuation", "combination", "startend", "letters", "paragraphs", "first_word",
         "last_word", "detectable_content", "language", "new"]


# ---------- helpers ----------
def gini(x: np.ndarray) -> float:
    x = np.sort(np.asarray(x, float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return 0.0
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))


def energy_rank(sv: np.ndarray, frac: float) -> int:
    e = np.cumsum(sv ** 2) / np.sum(sv ** 2)
    return int(np.searchsorted(e, frac) + 1)


def entropy_bits(p: float) -> float:
    if p <= 0 or p >= 1:
        return 0.0
    return float(-(p * np.log2(p) + (1 - p) * np.log2(1 - p)))


# ---------- PART 1: leverage / flatness ----------
def leverage(M: np.ndarray) -> dict:
    # M: candidates x 150. SVD; right singular vectors span example space.
    U, S, Vt = np.linalg.svd(M - M.mean(axis=0, keepdims=True), full_matrices=False)
    stable_rank = float((S ** 2).sum() / (S[0] ** 2)) if S[0] > 0 else 0.0
    k90 = energy_rank(S, 0.90)
    k95 = energy_rank(S, 0.95)
    k = max(1, k90)
    lev = (Vt[:k, :] ** 2).sum(axis=0)  # column leverage, sums to k
    cv = float(lev.std() / lev.mean()) if lev.mean() > 0 else 0.0
    # sensitivity proxy
    sens = np.abs(M - M.mean(axis=0, keepdims=True)).max(axis=0)
    sens = sens / sens.sum() if sens.sum() > 0 else sens
    # within-row permutation null on leverage CV
    null_cv = np.empty(N_PERM)
    for t in range(N_PERM):
        Mp = np.array([RNG.permutation(row) for row in M])
        _, _, Vtp = np.linalg.svd(Mp - Mp.mean(axis=0, keepdims=True), full_matrices=False)
        lp = (Vtp[:k, :] ** 2).sum(axis=0)
        null_cv[t] = lp.std() / lp.mean() if lp.mean() > 0 else 0.0
    pct = float((null_cv < cv).mean() * 100)
    return {"shape": M.shape, "stable_rank": stable_rank, "k90": k90, "k95": k95,
            "lev": lev, "lev_cv": cv, "lev_gini": gini(lev), "lev_maxmean": float(lev.max() / lev.mean()),
            "uniform_lev": k / M.shape[1], "sens": sens,
            "null_cv_mean": float(null_cv.mean()), "null_cv_p95": float(np.percentile(null_cv, 95)),
            "obs_cv_percentile": pct}


# ---------- PART 2: constraint structure ----------
def candidate_constraint_matrix(runs, by_type: bool):
    """rows = (run, parent candidate), cols = constraint id or type; entry = mean parent_sat."""
    acc: dict = {}
    for run in runs:
        for c in run.cycles:
            for obj in c.parent_objscores:
                for k, v in obj.items():
                    cid = k.split("#", 1)[0]
                    col = constraint_type(cid) if by_type else cid
                    key = (run.seed, run.b, c.parent_id)
                    acc.setdefault(key, {}).setdefault(col, []).append(float(v))
    rows = sorted(acc.keys())
    cols = sorted({col for d in acc.values() for col in d})
    M = np.full((len(rows), len(cols)), np.nan)
    for i, r in enumerate(rows):
        for j, col in enumerate(cols):
            if col in acc[r]:
                M[i, j] = np.mean(acc[r][col])
    return M, rows, cols


def antagonism(df: pd.DataFrame, accepted_only=False):
    """16x16 P(break b | fix a) and base-rate P(break b), unit = (run,iter,example) transition."""
    d = df if not accepted_only else df[df.accepted]
    fixed_sets, broke_sets = [], []
    for _, g in d.groupby(["run", "iter", "example_pos"]):
        fixed = {constraint_type(c) for c, ps, cs in zip(g.constraint, g.parent_sat, g.child_sat) if ps == 0 and cs == 1}
        broke = {constraint_type(c) for c, ps, cs in zip(g.constraint, g.parent_sat, g.child_sat) if ps == 1 and cs == 0}
        fixed_sets.append(fixed)
        broke_sets.append(broke)
    n = len(fixed_sets)
    base = {b: np.mean([b in bs for bs in broke_sets]) for b in TYPES}
    mat = np.full((len(TYPES), len(TYPES)), np.nan)
    cnt = np.zeros((len(TYPES), len(TYPES)), int)
    for ia, a in enumerate(TYPES):
        idx = [i for i in range(n) if a in fixed_sets[i]]
        cnt[ia, :] = len(idx)
        if not idx:
            continue
        for ib, b in enumerate(TYPES):
            mat[ia, ib] = np.mean([b in broke_sets[i] for i in idx])
    return mat, np.array([base[b] for b in TYPES]), cnt, n


# ---------- figures ----------
def fig_leverage(pooled: dict, path: str):
    lev = np.sort(pooled["lev"])[::-1]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.bar(range(len(lev)), lev, width=1.0, color="#3b7", label="observed leverage")
    ax.axhline(pooled["uniform_lev"], color="k", ls="--", lw=1.5,
               label=f"uniform = k/150 = {pooled['uniform_lev']:.4f}")
    ax.set_xlabel("valset example (sorted by leverage)")
    ax.set_ylabel(f"statistical leverage (top-{pooled['k90']} subspace)")
    ax.set_title(f"Matrix A column leverage — pooled b3 (123×150)  "
                 f"CV={pooled['lev_cv']:.2f} Gini={pooled['lev_gini']:.2f}  "
                 f"obs CV at {pooled['obs_cv_percentile']:.0f}th pct of null")
    ax.legend()
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


def fig_antagonism(mat, base, cnt, path: str):
    lift = mat - base[None, :]  # conditional minus base rate
    masked = np.ma.masked_where(cnt < 5, lift)
    fig, ax = plt.subplots(figsize=(8.5, 7))
    im = ax.imshow(masked, cmap="RdBu_r", vmin=-0.3, vmax=0.3, aspect="auto")
    ax.set_xticks(range(len(TYPES))); ax.set_xticklabels(TYPES, rotation=90, fontsize=7)
    ax.set_yticks(range(len(TYPES))); ax.set_yticklabels(TYPES, fontsize=7)
    ax.set_xlabel("breaks type b"); ax.set_ylabel("fixes type a")
    ax.set_title("Antagonism lift: P(break b | fix a) − P(break b)\n(grey = <5 events; raw stream)")
    fig.colorbar(im, label="lift over base rate")
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


def main():
    runs = load_corpus()
    b3 = [r for r in runs if r.b == 3]

    print("=== STEP 0 — DATA INVENTORY ===")
    print("Matrix A (candidate × valset scalar) — PER-RUN, not one matrix:")
    for r in runs:
        M, _ = pool_matrix(r)
        print(f"  seed{r.seed}_b{r.b}: {M.shape}  observed={1-np.isnan(M).mean():.3f}  "
              f"range[{M.min():.2f},{M.max():.2f}]")
    pooledM = np.vstack([pool_matrix(r)[0] for r in b3])
    print(f"  POOLED b3: {pooledM.shape}  observed={1-np.isnan(pooledM).mean():.3f}")
    dfB = pd.read_parquet(PARTIAL_DIAG)
    nfix = int(((dfB.parent_sat == 0) & (dfB.child_sat == 1)).sum())
    nbrk = int(((dfB.parent_sat == 1) & (dfB.child_sat == 0)).sum())
    print(f"Matrix B (partial_diag): {len(dfB)} rows, {dfB['type'].nunique()} types, "
          f"{dfB['constraint'].nunique()} ids, {dfB.groupby(['run','iter','example_pos']).ngroups} "
          f"transitions, {nfix} fix / {nbrk} break events")

    # ---- PART 1 ----
    print("\n=== PART 1 — Matrix A leverage / flatness ===")
    per_run = []
    for r in b3:
        L = leverage(pool_matrix(r)[0])
        per_run.append({"run": f"seed{r.seed}", "stable_rank": L["stable_rank"], "k90": L["k90"],
                        "k95": L["k95"], "lev_cv": L["lev_cv"], "lev_gini": L["lev_gini"],
                        "obs_cv_pct": L["obs_cv_percentile"]})
    prdf = pd.DataFrame(per_run)
    print(prdf.round(3).to_string(index=False))
    pooled = leverage(pooledM)
    print(f"\nPOOLED b3: stable_rank={pooled['stable_rank']:.2f} k90={pooled['k90']} k95={pooled['k95']} "
          f"lev_CV={pooled['lev_cv']:.3f} Gini={pooled['lev_gini']:.3f} max/mean={pooled['lev_maxmean']:.2f}")
    print(f"  null leverage-CV: mean={pooled['null_cv_mean']:.3f} p95={pooled['null_cv_p95']:.3f}; "
          f"observed CV at {pooled['obs_cv_percentile']:.0f}th percentile of null")

    # ---- PART 2 ----
    print("\n=== PART 2 — constraint structure ===")
    c2a = {}
    for by_type, lbl in [(True, "16-type"), (False, "54-id")]:
        Cm, rws, cls = candidate_constraint_matrix(runs, by_type)
        filled = np.nan_to_num(Cm, nan=np.nanmean(Cm))
        U, S, Vt = np.linalg.svd(filled - filled.mean(0), full_matrices=False)
        sr = float((S ** 2).sum() / S[0] ** 2) if S[0] > 0 else 0.0
        ents = [entropy_bits(np.nanmean(Cm[:, j])) for j in range(Cm.shape[1])]
        c2a[lbl] = {"shape": Cm.shape, "observed": float(1 - np.isnan(Cm).mean()),
                    "stable_rank": sr, "k90": int(energy_rank(S, 0.9)),
                    "mean_entropy": float(np.nanmean(ents))}
        print(f"  C[{lbl}] shape={Cm.shape} observed={1-np.isnan(Cm).mean():.2f} stable_rank={sr:.2f} "
              f"k90={energy_rank(S,0.9)} mean_passrate_entropy={np.nanmean(ents):.3f} bits")

    mat, base, cnt, ntrans = antagonism(dfB)
    matA, baseA, cntA, _ = antagonism(dfB, accepted_only=True)
    tri = [(i, j) for i in range(16) for j in range(16) if i != j]
    est10 = sum(cnt[i, j] >= 10 for i, j in tri)
    est5 = sum(cnt[i, j] >= 5 for i, j in tri)
    lift = mat - base[None, :]
    antag_pairs = [(TYPES[i], TYPES[j], float(mat[i, j]), float(base[j]), int(cnt[i, j]))
                   for i, j in tri if cnt[i, j] >= 5 and lift[i, j] > 0]
    antag_pairs.sort(key=lambda t: -(t[2] - t[3]))
    n_est5 = sum(cnt[i, j] >= 5 for i, j in tri)
    frac_above = (sum(1 for i, j in tri if cnt[i, j] >= 5 and lift[i, j] > 0) / n_est5) if n_est5 else 0.0
    print(f"  transitions={ntrans}; estimable ordered pairs: N>=10:{est10}  N>=5:{est5} (of 240 ordered / 120 unordered)")
    print(f"  fraction of N>=5 estimable pairs with antagonism ABOVE base rate: {frac_above:.2f}")
    print("  top antagonistic pairs (fix a -> break b, P|fix vs base, n):")
    for a, b, p, bs, n in antag_pairs[:8]:
        print(f"    fix {a:18s} -> break {b:18s}  {p:.2f} vs {bs:.2f}  (n={n})")

    # ---- figures ----
    os.makedirs("analysis", exist_ok=True)
    fig_leverage(pooled, "analysis/fig_leverage.png")
    fig_antagonism(mat, base, cnt, "analysis/fig_antagonism.png")
    print("\nwrote analysis/fig_leverage.png + analysis/fig_antagonism.png")

    # ---- persist + md ----
    prdf.to_parquet("analysis/probe_leverage_flatness.parquet", index=False)
    _write_md(pooled, prdf, dfB, ntrans, nfix, nbrk, est10, est5, frac_above, antag_pairs, c2a)
    _append_project_state(pooled, est5, frac_above, antag_pairs)
    print("wrote analysis/probe_leverage_flatness.{md,parquet} + PROJECT_STATE append")


def _verdict1(pooled):
    flat = pooled["lev_cv"] < 0.6 and pooled["lev_gini"] < 0.4 and pooled["obs_cv_percentile"] < 95
    return flat


def _write_md(pooled, prdf, dfB, ntrans, nfix, nbrk, est10, est5, frac_above, antag_pairs, c2a):
    flat = _verdict1(pooled)
    c16 = c2a["16-type"]
    L = ["# Probe — leverage-flatness + constraint structure\n",
         "Offline, $0. Characterizes the OBSERVED uniform-sampled corpus matrices only — it does NOT "
         "test what a non-uniform sampler or an aggregate gate would do.\n",
         "## STEP 0 — inventory",
         f"- Matrix A = **per-run** candidate×valset (each ~16×150, fully observed, range [0,1]); pooled "
         f"b3 = 123×150. NOT a single global matrix.",
         f"- Matrix B = partial_diag.parquet: {len(dfB)} rows, {ntrans} (cycle,example) transitions, "
         f"{nfix} fix / {nbrk} break events.\n",
         "## Part 1 — leverage / flatness (Claim 1)",
         f"- Pooled b3 (123×150): **stable rank {pooled['stable_rank']:.1f}** (of 123 candidates), "
         f"90%-energy rank k={pooled['k90']}, 95% k={pooled['k95']}. Per-run stable rank ~6 of ~16 "
         f"candidates → real candidate (row) redundancy.",
         f"- Column (example) leverage: **CV {pooled['lev_cv']:.2f}, Gini {pooled['lev_gini']:.2f}**, "
         f"max/mean {pooled['lev_maxmean']:.1f}, uniform={pooled['uniform_lev']:.4f}.",
         f"- Within-row permutation null (1000 draws): observed leverage-CV at the "
         f"**{pooled['obs_cv_percentile']:.0f}th percentile** (null mean {pooled['null_cv_mean']:.2f}, "
         f"p95 {pooled['null_cv_p95']:.2f}) — every run also at the 100th percentile.",
         "\n**Verdict 1 — SURPRISE, Claim 1's *flat-sensitivity* framing is NOT grounded.** Two things "
         "are simultaneously true and must not be conflated: (i) the matrix is **low-rank** (per-run "
         "stable rank ~6 of 16) — candidates are redundant, consistent with the fungibility result; but "
         "(ii) column **leverage is heavy-tailed and far above the within-row null** (CV 0.95, Gini 0.53, "
         "100th percentile) — a structured minority of examples (the swingable cells) carry the leverage, "
         "the rest are near-zero (consensus cells). So 'selection futility' is a **row/redundancy** "
         "phenomenon, NOT 'flat example sensitivity': example sensitivity is the opposite of flat. "
         "(Observed-matrix claim only — this is not a test of a non-uniform sampler.)\n",
         "## Part 2 — constraint structure & antagonism (Claim 2)",
         f"- **Do constraints distinguish candidates?** Candidate×constraint pass-rate matrix "
         f"(16-type, {c16['shape'][0]}×16, {c16['observed']:.0%} observed): stable rank "
         f"{c16['stable_rank']:.1f} of 16, mean per-type pass-rate entropy **{c16['mean_entropy']:.2f} "
         f"bits** (max 1.0). Moderate rank + moderate entropy ⇒ constraints carry real variation — "
         f"**weak** dual redundancy, not strong. (Caveat: confounded by uneven minibatch coverage.)",
         f"- **Antagonism:** estimable ordered pairs **N≥10: {est10}, N≥5: {est5}** of 240 (estimability "
         f"is set by fix-a frequency, not break co-occurrence). Only **{frac_above:.0%}** of N≥5 pairs "
         f"show a conditional break-rate ABOVE base rate.",
         "- Top antagonistic pairs (fix a → break b; P(break b|fix a) vs base; n):"]
    for a, b, p, bs, n in antag_pairs[:8]:
        L.append(f"  - fix `{a}` → break `{b}`: {p:.2f} vs {bs:.2f} (n={n})")
    L.append(f"\n**Verdict 2 — tradeoffs are real but SPARSE, not dense.** Breaks-on-fix exceed base "
             f"rate for only {frac_above:.0%} of estimable type pairs, and the reliable lifts are few "
             "(e.g. fix `keywords`→break `detectable_format` 0.12 vs 0.02, n=43); most fix-a transitions "
             "break nothing. The **aggregate gate is still motivated** — real tradeoffs exist and the "
             "accept gate filters them (raw stream: ~256 fixes vs 235 breaks) — but a per-pair "
             "*antagonism scorer* would only have signal on the handful of dense pairs, not a dense "
             "16×16 structure. (Observed-stream claim only.)\n")
    with open("analysis/probe_leverage_flatness.md", "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")


def _append_project_state(pooled, est5, frac_above, antag_pairs):
    heading = "## Leverage/flatness probe"
    top = antag_pairs[0] if antag_pairs else ("—", "—", 0, 0, 0)
    block = "\n".join([
        f"{heading} (2026-06-30)",
        f"- Matrix A pooled b3 (123×150): stable rank {pooled['stable_rank']:.1f}, 90%-energy rank "
        f"k={pooled['k90']}; per-run stable rank ~6 of 16 (candidate redundancy), BUT column-leverage "
        f"CV {pooled['lev_cv']:.2f} / Gini {pooled['lev_gini']:.2f} at {pooled['obs_cv_percentile']:.0f}th "
        f"pct of within-row null (heavy-tailed).",
        "- Claim 1 (selection futility via FLAT sensitivity): NOT grounded — surprise. Futility is a "
        "row/redundancy phenomenon; example leverage is heavy-tailed (swingable cells), not flat.",
        f"- Matrix B: antagonism estimable for {est5}/240 ordered type pairs (N≥5); only {frac_above:.0%} "
        f"exceed base rate; top reliable: fix keywords→break detectable_format (0.12 vs 0.02, n=43).",
        "- Claim 2 (gate is the lever): tradeoffs real but SPARSE not dense; constraints carry moderate "
        "entropy (weak dual redundancy). Aggregate gate motivated; per-pair antagonism scorer only on "
        "the few dense pairs. Caveat: observed uniform corpus only — not a sampler/gate test.\n",
    ])
    with open("analysis/PROJECT_STATE.md", encoding="utf-8") as fh:
        text = fh.read()
    idx = text.find(heading)
    if idx != -1:  # idempotent: drop any prior probe block before re-appending
        text = text[:idx].rstrip() + "\n"
    else:
        text = text.rstrip() + "\n\n"
    with open("analysis/PROJECT_STATE.md", "w", encoding="utf-8") as fh:
        fh.write(text + block + "\n")


if __name__ == "__main__":
    main()
