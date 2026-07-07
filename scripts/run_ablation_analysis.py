"""Feedback-ablation Stage 2 — pre-registered analysis ($0, reads calls.csv).

Primary: accept rate (i)vs(iii) & (i)vs(ii), McNemar + sign-flip permutation (>=10k).
Secondary: gate margin (child-parent) paired permutation. Lottery: (i)vs(i_rep). Independent 2nd-path
recompute of the accept table. Logged-parent cross-check from corpus_io before_scores.

Run: HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/run_ablation_analysis.py
"""
from __future__ import annotations

import csv
import collections

import numpy as np
from scipy import stats

from gepa_si.screen.corpus_io import load_corpus

rng = np.random.default_rng(0)
rows = list(csv.DictReader(open("analysis/ablation/calls.csv")))

# ---- pivot per batch: arm -> (accept, margin) ----
bat = collections.defaultdict(dict)
key_of = {}
for r in rows:
    b = r["batch_id"]; arm = r["arm"]
    c = float(r["child_score_sum"]); p = float(r["parent_score_sum_today"])
    bat[b][arm] = {"accept": int(c > p), "margin": c - p, "child": c, "parent": p}
    key_of[b] = (int(r["seed"]), int(r["iteration"]))

# ---- logged parent scores (cross-check): sum before_scores per (seed, iteration) ----
logged_parent = {}
for run in load_corpus():
    if run.b != 3:
        continue
    for cyc in run.cycles:
        logged_parent[(run.seed, cyc.iteration)] = float(sum(cyc.before_scores))

bids = sorted(bat)
print(f"batches={len(bids)}  arms present: {collections.Counter(a for b in bat.values() for a in b)}")


def accept_arr(arm):
    return np.array([bat[b][arm]["accept"] for b in bids if arm in bat[b]])


def paired(arm1, arm2, field):
    xs, ys = [], []
    for b in bids:
        if arm1 in bat[b] and arm2 in bat[b]:
            xs.append(bat[b][arm1][field]); ys.append(bat[b][arm2][field])
    return np.array(xs), np.array(ys)


# ---- accept rates ----
print("\n=== accept rates by arm (child beats parent-today) ===")
rates = {}
for arm in ["i", "ii", "iii"]:
    a = accept_arr(arm); rates[arm] = a.mean()
    print(f"  arm {arm:3}: accept {a.mean():.3f}  ({a.sum()}/{len(a)})")
parent_today_mean = np.mean([bat[b]["i"]["parent"] for b in bids])
logged_mean = np.mean([logged_parent[key_of[b]] for b in bids])
print(f"  [cross-check] mean parent sum today={parent_today_mean:.3f} vs logged={logged_mean:.3f}")


def mcnemar_perm(arm1, arm2, nperm=20000):
    x, y = paired(arm1, arm2, "accept")
    diff = x.mean() - y.mean()
    disc = x != y
    nd = int(disc.sum())
    b_ = int(((x == 1) & (y == 0)).sum()); c_ = int(((x == 0) & (y == 1)).sum())
    # exact binomial McNemar on discordant
    k = min(b_, c_); pmc = min(1.0, 2 * stats.binom.cdf(k, b_ + c_, 0.5)) if (b_ + c_) else 1.0
    # sign-flip permutation on discordant pairs -> null dist of the marginal accept-rate diff
    null = []
    base_equal = (~disc).sum()
    for _ in range(nperm):
        flips = rng.integers(0, 2, nd)  # 1 -> arm1 accepts, 0 -> arm2 accepts among discordant
        b2 = flips.sum(); c2 = nd - b2
        null.append((b2 - c2) / len(x))
    null = np.array(null); pperm = float((np.abs(null) >= abs(diff) - 1e-12).mean())
    return diff, b_, c_, nd, pmc, pperm


print("\n=== PRIMARY: accept-rate McNemar + permutation ===")
prim = {}
for pair in [("i", "iii"), ("i", "ii")]:
    d, b_, c_, nd, pmc, pp = mcnemar_perm(*pair)
    prim[pair] = (d, pmc, pp)
    print(f"  {pair[0]} vs {pair[1]}: Δaccept={d:+.3f}  discordant b/c={b_}/{c_} (n_disc={nd})  "
          f"McNemar p={pmc:.3f}  perm p={pp:.3f}")


def margin_perm(arm1, arm2, nperm=20000):
    x, y = paired(arm1, arm2, "margin")
    d = x - y; obs = d.mean()
    null = np.array([(d * rng.choice([-1, 1], len(d))).mean() for _ in range(nperm)])
    return obs, float((np.abs(null) >= abs(obs) - 1e-12).mean())


print("\n=== SECONDARY: gate margin (child-parent), paired sign-flip permutation ===")
for arm in ["i", "ii", "iii"]:
    m = np.array([bat[b][arm]["margin"] for b in bids if arm in bat[b]])
    print(f"  arm {arm:3}: mean margin {m.mean():+.4f}")
for pair in [("i", "ii"), ("i", "iii")]:
    obs, pp = margin_perm(*pair)
    print(f"  Δmargin {pair[0]}-{pair[1]} = {obs:+.4f}  perm p={pp:.3f}")

# ---- lottery share: i vs i_rep on the 50 subset ----
print("\n=== LOTTERY: (i) vs (i_rep) on seed-repeat subset ===")
rep = [b for b in bids if "i_rep" in bat[b]]
xa = np.array([bat[b]["i"]["accept"] for b in rep]); xr = np.array([bat[b]["i_rep"]["accept"] for b in rep])
ma = np.array([bat[b]["i"]["margin"] for b in rep]); mr = np.array([bat[b]["i_rep"]["margin"] for b in rep])
disagree = (xa != xr).mean()
lottery_var = np.var(ma - mr) / 2                       # per-call sampling variance of the margin
arm_effect_var = np.var([rates["i"] - rates["iii"], rates["i"] - rates["ii"]])  # crude arm-effect scale
print(f"  n_repeat={len(rep)}  accept-disagreement rate (same arm, diff draw) = {disagree:.3f}")
print(f"  margin lottery variance (within arm i) = {lottery_var:.4f}  vs |arm effects| ~ {abs(prim[('i','iii')][0]):.3f}/{abs(prim[('i','ii')][0]):.3f} accept-pp")

# ---- independent 2nd-path recompute of accept table ----
print("\n=== INDEPENDENT recompute (2nd path) of accept rates ===")
import pandas as pd
df = pd.read_csv("analysis/ablation/calls.csv")
df["acc2"] = (df.child_score_sum > df.parent_score_sum_today).astype(int)
for arm in ["i", "ii", "iii"]:
    sub = df[df.arm == arm]
    print(f"  arm {arm:3}: accept {sub.acc2.mean():.3f}  (matches primary: {abs(sub.acc2.mean()-rates[arm])<1e-9})")

# save summary
with open("analysis/ablation/analysis_summary.csv", "w", newline="") as f:
    w = csv.writer(f); w.writerow(["metric", "value"])
    for arm in ["i", "ii", "iii"]:
        w.writerow([f"accept_rate_{arm}", rates[arm]])
    for pair in [("i", "iii"), ("i", "ii")]:
        d, pmc, pp = prim[pair]; w.writerow([f"delta_accept_{pair[0]}v{pair[1]}", d]); w.writerow([f"perm_p_{pair[0]}v{pair[1]}", pp])
    w.writerow(["lottery_accept_disagreement", disagree]); w.writerow(["spend_usd", 7.7399])
print("\nDONE — wrote analysis/ablation/analysis_summary.csv")
