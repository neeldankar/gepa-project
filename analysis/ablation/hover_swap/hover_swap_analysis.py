"""Stage-2 HoVer batch-swap — Phase 3 pre-registered analysis ($0; reads pairs/*/draws.jsonl).

Port of scripts/batch_swap_v2_analysis.py. Estimand definitions unchanged (brief line 22/111);
adapted only for the HoVer metric (title-recall on {0,1/3,2/3,1}) and the A_e/B_e naming.

  v2 -> HoVer:  B -> A_e     B' -> B_e     arm R_B -> SAME     arm R_Bp -> SWAP

Estimands (draw-averaged margins; margin = child - parent baseline on the batch being scored,
summed over the 3 examples — batch_swap_v2_run.py:222,232-235):
  SPECIFICITY_A = margin(SAME on A) - margin(SWAP on A)   (both on A -> parent cancels)
  SPECIFICITY_B = margin(SWAP on B) - margin(SAME on B)   (symmetric replication)
  pooled specificity = mean of the two ; pooled transfer = mean(margin(SAME on B), margin(SWAP on A))
Inference: within-pair sign-flip permutation AND run-level cluster bootstrap over the 8 seeds.
MDE = Z80 * SE_clustered (Z80=2.802 verbatim from batch_swap_v2_stage0.py:36); v2's SIG2 constant
is IFBench-measured and does not port.

Scores lie exactly on {0,1/3,2/3,1}, so all margins are computed in INTEGER THIRDS: tie counts
("exactly 0") are exact, with no float tolerance.

NOT ported (see results.md provenance): overlap decomposition (no constraint types on HoVer),
failure-count sensitivity (different B_e construction), lottery (embeds >0 accept logic the
brief's Ties section forbids), verdict()/interpretation cell (brief line 112).

  scratch/hover_probe/.venv/bin/python analysis/ablation/hover_swap/hover_swap_analysis.py
"""
from __future__ import annotations

import collections
import json
import os

import numpy as np

OUT = "analysis/ablation/hover_swap"
PAIRS = f"{OUT}/pairs"
NPERM, NBOOT = 20000, 20000
Z80 = 2.802  # z_{.975}+z_{.80}, two-sided 80%-power MDE (batch_swap_v2_stage0.py:36)
K = 3
EXPECTED_PER_SEED = [32, 34, 28, 33, 27, 34, 28, 27]  # brief line 70
rng = np.random.default_rng(20260703)


def thirds(xs):
    """Exact integer-thirds representation of a score vector (asserts on-lattice)."""
    out = []
    for v in xs:
        t = round(v * 3)
        assert abs(v * 3 - t) < 1e-9, f"score {v} is not a multiple of 1/3"
        out.append(int(t))
    return out


def load():
    """Return rows: one dict per draw, margins in integer thirds."""
    rows = []
    per_seed = collections.Counter()
    pair_ids = sorted(os.listdir(PAIRS))
    for pid in pair_ids:
        drawf = f"{PAIRS}/{pid}/draws.jsonl"
        if not os.path.exists(drawf):
            continue
        rs = [json.loads(l) for l in open(drawf)]
        assert len(rs) == 2 * K, f"{pid}: {len(rs)} draw rows, expected {2*K}"
        arms = collections.Counter(r["arm"] for r in rs)
        assert arms == {"SAME": K, "SWAP": K}, f"{pid}: arm counts {dict(arms)}"
        per_seed[rs[0]["seed"]] += 1
        for r in rs:
            cA, cB = thirds(r["scores_on_A_e"]), thirds(r["scores_on_B_e"])
            pA, pB = thirds(r["A_e_parent_scores_logged"]), thirds(r["B_e_parent_scores_fresh"])
            rows.append(dict(
                pair=pid, seed=r["seed"], arm=r["arm"], draw=r["draw"],
                margin_on_A=sum(cA) - sum(pA),          # integer thirds
                margin_on_B=sum(cB) - sum(pB),          # integer thirds
                child_A=sum(cA), child_B=sum(cB),
                delta_A=[c - p for c, p in zip(cA, pA)],  # per-example, integer thirds
                delta_B=[c - p for c, p in zip(cB, pB)],
            ))
    got = [per_seed[i] for i in range(8)]
    assert got == EXPECTED_PER_SEED, f"per-seed counts {got} != {EXPECTED_PER_SEED}"
    assert len(rows) == 243 * 2 * K, f"{len(rows)} draw rows, expected {243*2*K}"
    return rows


def draw_avg(rs, arm, field):
    """v2 draw_avg, verbatim (batch_swap_v2_analysis.py:26)."""
    v = [float(r[field]) for r in rs if r["arm"] == arm]
    return float(np.mean(v)) if v else np.nan


def perm_p(x):
    """Within-pair sign-flip permutation two-sided p for H0 mean=0 (v2, verbatim)."""
    x = np.asarray(x)
    obs = x.mean()
    null = np.array([(x * rng.choice([-1.0, 1.0], len(x))).mean() for _ in range(NPERM)])
    return obs, float((np.abs(null) >= abs(obs) - 1e-12).mean())


def cluster_boot(x, clusters):
    """Run-level cluster bootstrap: resample whole seeds with replacement (v2, verbatim).

    Returns (lo, hi, se) — se is the SD of the bootstrap means, used for the MDE.
    """
    x = np.asarray(x)
    clusters = np.asarray(clusters)
    uniq = np.unique(clusters)
    by = {c: x[clusters == c] for c in uniq}
    means = []
    for _ in range(NBOOT):
        pick = rng.choice(uniq, len(uniq), replace=True)
        means.append(np.concatenate([by[c] for c in pick]).mean())
    means = np.asarray(means)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5)), float(means.std(ddof=1))


def main():
    rows = load()
    by_pair = collections.defaultdict(list)
    for r in rows:
        by_pair[r["pair"]].append(r)
    print(f"pairs={len(by_pair)}  draws/arm K={K}  clusters={len({r['seed'] for r in rows})}")

    # ---- primary route: per-pair draw-averaged margins (integer thirds -> /3 for score units) ----
    spec, transf, clusters, pids = [], [], [], []
    for pid, rs in sorted(by_pair.items()):
        mA_SAME = draw_avg(rs, "SAME", "margin_on_A")
        mA_SWAP = draw_avg(rs, "SWAP", "margin_on_A")
        mB_SAME = draw_avg(rs, "SAME", "margin_on_B")
        mB_SWAP = draw_avg(rs, "SWAP", "margin_on_B")
        if np.any(np.isnan([mA_SAME, mA_SWAP, mB_SAME, mB_SWAP])):
            continue
        spec.append((((mA_SAME - mA_SWAP) + (mB_SWAP - mB_SAME)) / 2) / 3.0)  # pooled specificity
        transf.append(((mB_SAME + mA_SWAP) / 2) / 3.0)                        # pooled transfer
        clusters.append(rs[0]["seed"])
        pids.append(pid)
    spec, transf, clusters = np.array(spec), np.array(transf), np.array(clusters)

    def report(name, x):
        obs, p = perm_p(x)
        lo, hi, se = cluster_boot(x, clusters)
        nlo, nhi = np.percentile([np.mean(rng.choice(x, len(x))) for _ in range(NBOOT)], [2.5, 97.5])
        mde = Z80 * se
        print(f"\n== {name} ==")
        print(f"  point={obs:+.4f}  perm p={p:.4f}")
        print(f"  95% CI: cluster-boot(run)=[{lo:+.4f},{hi:+.4f}]  naive-pair=[{nlo:+.4f},{nhi:+.4f}]")
        print(f"  SE_clustered={se:.4f}  MDE=Z80*SE={mde:.4f}")
        return dict(point=obs, p=p, clo=lo, chi=hi, nlo=nlo, nhi=nhi, se=se, mde=mde)

    S = report("POOLED SPECIFICITY", spec)
    T = report("POOLED TRANSFER", transf)

    # ---- baseline-cancellation check: specificity from raw child sums only ----
    spec_nobase = []
    for pid, rs in sorted(by_pair.items()):
        cA_S, cA_W = draw_avg(rs, "SAME", "child_A"), draw_avg(rs, "SWAP", "child_A")
        cB_S, cB_W = draw_avg(rs, "SAME", "child_B"), draw_avg(rs, "SWAP", "child_B")
        spec_nobase.append((((cA_S - cA_W) + (cB_W - cB_S)) / 2) / 3.0)
    cancel_max = float(np.max(np.abs(np.array(spec_nobase) - spec)))
    print(f"\n== baseline cancellation (specificity from child sums only) max|diff| = {cancel_max:.2e} ==")

    # ---- independent 2nd-path recompute (pandas groupby route), BOTH estimands ----
    import pandas as pd
    df = pd.DataFrame(rows)
    piv = df.groupby(["pair", "arm"])[["margin_on_A", "margin_on_B"]].mean()

    def g(pid, arm, col):
        return piv.loc[(pid, arm), col]

    spec2 = np.array([((((g(p, "SAME", "margin_on_A") - g(p, "SWAP", "margin_on_A")) +
                         (g(p, "SWAP", "margin_on_B") - g(p, "SAME", "margin_on_B"))) / 2) / 3.0)
                      for p in pids])
    transf2 = np.array([(((g(p, "SAME", "margin_on_B") + g(p, "SWAP", "margin_on_A")) / 2) / 3.0)
                        for p in pids])
    dS = abs(float(np.nanmean(spec2)) - S["point"])
    dT = abs(float(np.nanmean(transf2)) - T["point"])
    print(f"\n== 2nd-path recompute ==")
    print(f"  specificity {np.nanmean(spec2):+.6f} vs {S['point']:+.6f}  delta={dS:.3e}")
    print(f"  transfer    {np.nanmean(transf2):+.6f} vs {T['point']:+.6f}  delta={dT:.3e}")
    assert dS < 1e-9 and dT < 1e-9, "second-path recompute disagrees with primary"

    # ---- tie shares (exact, integer thirds) ----
    dA = [d for r in rows for d in r["delta_A"]]
    dB = [d for r in rows for d in r["delta_B"]]
    own = [d for r in rows for d in (r["delta_A"] if r["arm"] == "SAME" else r["delta_B"])]
    oth = [d for r in rows for d in (r["delta_B"] if r["arm"] == "SAME" else r["delta_A"])]
    all_delta = dA + dB
    margins = [r["margin_on_A"] for r in rows] + [r["margin_on_B"] for r in rows]

    def z(v):
        return float(np.mean([x == 0 for x in v]))

    ties = dict(delta_all=(z(all_delta), len(all_delta)), delta_own=(z(own), len(own)),
                delta_other=(z(oth), len(oth)), margin_all=(z(margins), len(margins)))
    print(f"\n== TIE SHARES (exact, integer thirds) ==")
    for k, (s, n) in ties.items():
        print(f"  {k:12} share exactly 0 = {s:.4f}  (N={n})")

    # ---- results.md: numbers, CIs, MDEs, tie shares ONLY ----
    per_seed = collections.Counter(clusters.tolist())
    with open(f"{OUT}/results.md", "w") as f:
        w = f.write
        w("# Stage-2 HoVer batch-swap — results\n\n")
        w(f"Pairs = {len(spec)}. Draws/arm K = {K}. Run clusters = {len(per_seed)} seeds.\n")
        w(f"Per-seed pairs: {dict(sorted(per_seed.items()))}.\n")
        w(f"Draw rows = {len(rows)}. Score support = {{0, 1/3, 2/3, 1}}; margins computed in integer thirds.\n\n")

        w("## Pooled estimands\n\n")
        w("| estimand | point | 95% CI (run cluster-boot) | MDE | SE (clustered) | perm p (within-pair) | 95% CI (naive-pair) |\n")
        w("|---|---|---|---|---|---|---|\n")
        for nm, E in (("pooled specificity", S), ("pooled transfer", T)):
            w(f"| {nm} | {E['point']:+.4f} | [{E['clo']:+.4f}, {E['chi']:+.4f}] | {E['mde']:.4f} "
              f"| {E['se']:.4f} | {E['p']:.4f} | [{E['nlo']:+.4f}, {E['nhi']:+.4f}] |\n")
        w("\nUnits: title-recall score points, on v2's scale. Per-example scores lie in "
          "{0, 1/3, 2/3, 1}; a margin is the sum over the 3 examples of the batch (range [-3, +3]), "
          "matching `batch_swap_v2_run.py:235`. Margins are accumulated internally in integer "
          "thirds and divided by 3 to return to score points; they are not averaged per example.\n\n")

        w("## Second-path recompute\n\n")
        w("Independent aggregation route (pandas groupby on `(pair, arm)`) vs the primary "
          "per-pair dict/numpy route.\n\n")
        w("| estimand | primary | second path | abs delta |\n|---|---|---|---|\n")
        w(f"| pooled specificity | {S['point']:+.9f} | {float(np.nanmean(spec2)):+.9f} | {dS:.2e} |\n")
        w(f"| pooled transfer | {T['point']:+.9f} | {float(np.nanmean(transf2)):+.9f} | {dT:.2e} |\n\n")
        w(f"Baseline-cancellation check: pooled specificity recomputed from child sums alone "
          f"(parent terms dropped) differs from the baseline-subtracted value by "
          f"max |diff| = {cancel_max:.2e} across pairs.\n\n")

        w("## Tie shares\n\n")
        w("Counted exactly, in integer thirds.\n\n")
        w("| quantity | share exactly 0 | N |\n|---|---|---|\n")
        w(f"| per-example child-parent deltas (all) | {ties['delta_all'][0]:.4f} | {ties['delta_all'][1]} |\n")
        w(f"| per-example child-parent deltas (own batch) | {ties['delta_own'][0]:.4f} | {ties['delta_own'][1]} |\n")
        w(f"| per-example child-parent deltas (other batch) | {ties['delta_other'][0]:.4f} | {ties['delta_other'][1]} |\n")
        w(f"| batch margins | {ties['margin_all'][0]:.4f} | {ties['margin_all'][1]} |\n\n")

        w("## Provenance\n\n")
        w("Estimand definitions ported from `scripts/batch_swap_v2_analysis.py` without change "
          "(v2 `B`->`A_e`, `B'`->`B_e`, arm `R_B`->`SAME`, arm `R_Bp`->`SWAP`):\n\n")
        w("- margin = sum of the 3 per-example child scores minus the sum of the parent's scores "
          "on the same batch (`batch_swap_v2_run.py:222,232-235`).\n")
        w("- pooled specificity = mean of `margin(SAME on A) - margin(SWAP on A)` and "
          "`margin(SWAP on B) - margin(SAME on B)`.\n")
        w("- pooled transfer = mean of `margin(SAME on B)` and `margin(SWAP on A)`.\n")
        w("- `draw_avg`, `perm_p`, `cluster_boot`, `NPERM = NBOOT = 20000`, "
          "`rng = default_rng(20260703)` taken verbatim from v2.\n\n")
        w("MDE = `Z80 * SE_clustered`, `Z80 = 2.802` (verbatim, `batch_swap_v2_stage0.py:36`); "
          "`SE_clustered` is the standard deviation of the run-level cluster-bootstrap means. "
          "v2's `SIG2 = 0.0775` and `MDE_SPEC = {2: 0.040, 3: 0.033}` are single-draw margin "
          "variances measured on IFBench and are not carried over; v2 states no transfer MDE.\n\n")
        w("Components of `batch_swap_v2_analysis.py` not ported:\n\n")
        w("- Overlap decomposition (`specificity ~ type_jaccard`): HoVer has no constraint types.\n")
        w("- Failure-count sensitivity (`Bprime_fail_underPB`): v2 gated B' on at least 2 of 3 "
          "examples failing under the parent; B_e here is selected by parent-score-multiset match.\n")
        w("- Lottery (`accept = margin_on_B > 0`): the brief's Ties section states no strict->0 "
          "accept logic in the analysis path.\n")
        w("- `verdict()` and the conditional interpretation cell: the brief's Phase 3 states "
          "numbers, CIs and MDEs only.\n")
    print(f"\n[wrote {OUT}/results.md]")


if __name__ == "__main__":
    main()
