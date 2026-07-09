"""HoVer heterogeneity screen — 0.5 checksum recompute + Part 1 outcome table. $0.

0.5: independently recompute pooled specificity/transfer BY REUSING the verified Phase-3
code paths (import from hover_swap_analysis; per-pair assembly lifted verbatim from its
main(), hover_swap_analysis.py:122-135,137-146,151-195). Must match the committed
results.md to reported precision; mismatch => hard exit, STOP.

Part 1: per-event spec_i / trans_i / sign_i + tie diagnostics -> outcomes.csv. Numbers only.
No scorer join happens in Phase A.

RNG parity: hover_swap_analysis holds a module-level rng=default_rng(20260703) consumed in
main() in the order perm_p -> cluster_boot -> naive boot, specificity first then transfer.
This script consumes hsa.rng in exactly that order. Run under the SAME interpreter that
produced results.md (scratch/hover_probe/.venv), from the repo root:

  scratch/hover_probe/.venv/bin/python analysis/hover_screen/screen_part05_outcomes.py
"""
from __future__ import annotations

import collections
import csv
import json
import os
import sys

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(REPO)  # hover_swap_analysis paths are repo-root relative
sys.path.insert(0, os.path.join(REPO, "analysis", "ablation", "hover_swap"))
import hover_swap_analysis as hsa  # noqa: E402

OUTDIR = os.path.join(REPO, "analysis", "hover_screen")

# Committed results.md values (byte-read 2026-07-09), at the file's reported precision.
EXPECT = {
    "spec": dict(point="+0.0274", clo="+0.0149", chi="+0.0415", mde="0.0191", se="0.0068",
                 p="0.0177", nlo="+0.0048", nhi="+0.0501", second="+0.027434842"),
    "trans": dict(point="+0.0169", clo="-0.0040", chi="+0.0367", mde="0.0293", se="0.0104",
                  p="0.3120", nlo="-0.0149", nhi="+0.0489", second="+0.016918153"),
    "ties": dict(delta_all="0.6295", delta_own="0.6278", delta_other="0.6312", margin_all="0.3656"),
    "tie_ns": dict(delta_all=8748, delta_own=4374, delta_other=4374, margin_all=2916),
}

fails = []


def check(name, got_str, want_str):
    ok = got_str == want_str
    print(f"  {name:28} got {got_str:>14}  want {want_str:>14}  {'OK' if ok else 'MISMATCH'}")
    if not ok:
        fails.append(name)


def main():
    rows = hsa.load()
    by_pair = collections.defaultdict(list)
    for r in rows:
        by_pair[r["pair"]].append(r)

    # ---- per-pair assembly, lifted verbatim from hover_swap_analysis.main():123-135 ----
    spec, transf, clusters, pids = [], [], [], []
    for pid, rs in sorted(by_pair.items()):
        mA_SAME = hsa.draw_avg(rs, "SAME", "margin_on_A")
        mA_SWAP = hsa.draw_avg(rs, "SWAP", "margin_on_A")
        mB_SAME = hsa.draw_avg(rs, "SAME", "margin_on_B")
        mB_SWAP = hsa.draw_avg(rs, "SWAP", "margin_on_B")
        if np.any(np.isnan([mA_SAME, mA_SWAP, mB_SAME, mB_SWAP])):
            continue
        spec.append((((mA_SAME - mA_SWAP) + (mB_SWAP - mB_SAME)) / 2) / 3.0)
        transf.append(((mB_SAME + mA_SWAP) / 2) / 3.0)
        clusters.append(rs[0]["seed"])
        pids.append(pid)
    spec, transf, clusters_a = np.array(spec), np.array(transf), np.array(clusters)

    # ---- RNG-order-faithful replication of report() for spec then transfer (:137-149) ----
    print("===== 0.5 CHECKSUM RECOMPUTE vs committed results.md =====")
    results = {}
    for name, x in (("spec", spec), ("trans", transf)):
        obs, p = hsa.perm_p(x)
        lo, hi, se = hsa.cluster_boot(x, clusters_a)
        nlo, nhi = np.percentile([np.mean(hsa.rng.choice(x, len(x))) for _ in range(hsa.NBOOT)],
                                 [2.5, 97.5])
        mde = hsa.Z80 * se
        results[name] = dict(point=obs, p=p, clo=lo, chi=hi, nlo=nlo, nhi=nhi, se=se, mde=mde)
        E = EXPECT[name]
        check(f"{name}.point", f"{obs:+.4f}", E["point"])
        check(f"{name}.cluster_CI_lo", f"{lo:+.4f}", E["clo"])
        check(f"{name}.cluster_CI_hi", f"{hi:+.4f}", E["chi"])
        check(f"{name}.MDE", f"{mde:.4f}", E["mde"])
        check(f"{name}.SE_clustered", f"{se:.4f}", E["se"])
        check(f"{name}.perm_p", f"{p:.4f}", E["p"])
        check(f"{name}.naive_CI_lo", f"{nlo:+.4f}", E["nlo"])
        check(f"{name}.naive_CI_hi", f"{nhi:+.4f}", E["nhi"])

    # ---- deterministic second path (pandas groupby, :160-178) ----
    import pandas as pd
    df = pd.DataFrame(rows)
    piv = df.groupby(["pair", "arm"])[["margin_on_A", "margin_on_B"]].mean()

    def g(pid, arm, col):
        return piv.loc[(pid, arm), col]

    spec2 = np.array([((((g(p_, "SAME", "margin_on_A") - g(p_, "SWAP", "margin_on_A")) +
                         (g(p_, "SWAP", "margin_on_B") - g(p_, "SAME", "margin_on_B"))) / 2) / 3.0)
                      for p_ in pids])
    transf2 = np.array([(((g(p_, "SAME", "margin_on_B") + g(p_, "SWAP", "margin_on_A")) / 2) / 3.0)
                        for p_ in pids])
    check("spec.second_path", f"{float(np.nanmean(spec2)):+.9f}", EXPECT["spec"]["second"])
    check("trans.second_path", f"{float(np.nanmean(transf2)):+.9f}", EXPECT["trans"]["second"])

    # ---- tie shares (:181-195) ----
    own = [d for r in rows for d in (r["delta_A"] if r["arm"] == "SAME" else r["delta_B"])]
    oth = [d for r in rows for d in (r["delta_B"] if r["arm"] == "SAME" else r["delta_A"])]
    all_delta = [d for r in rows for d in r["delta_A"]] + [d for r in rows for d in r["delta_B"]]
    margins = [r["margin_on_A"] for r in rows] + [r["margin_on_B"] for r in rows]

    def z(v):
        return float(np.mean([x == 0 for x in v]))

    for key, v in (("delta_all", all_delta), ("delta_own", own), ("delta_other", oth),
                   ("margin_all", margins)):
        check(f"ties.{key}", f"{z(v):.4f}", EXPECT["ties"][key])
        check(f"ties.{key}.N", str(len(v)), str(EXPECT["tie_ns"][key]))

    if fails:
        print(f"\n0.5 FAILED — {len(fails)} mismatches: {fails}")
        print("STOP per pre-registration. No outcomes written.")
        sys.exit(1)
    print("\n0.5 PASSED — all cells match committed results.md at reported precision.")

    # ================================================================ Part 1
    print("\n===== PART 1: per-event outcome table =====")
    ev_index = json.load(open(os.path.join(OUTDIR, "events_index.json")))
    out_rows = []
    for i, pid in enumerate(pids):
        rs = by_pair[pid]
        seed = rs[0]["seed"]
        trace_i = int(pid.split("_i")[1])
        ev = ev_index[f"{seed}_{trace_i}"]
        deltas = [d for r in rs for d in r["delta_A"]] + [d for r in rs for d in r["delta_B"]]
        margs = [r["margin_on_A"] for r in rs] + [r["margin_on_B"] for r in rs]
        d_own = [d for r in rs for d in (r["delta_A"] if r["arm"] == "SAME" else r["delta_B"])]
        d_oth = [d for r in rs for d in (r["delta_B"] if r["arm"] == "SAME" else r["delta_A"])]
        s = float(spec[i])
        out_rows.append(dict(
            pair_id=pid, seed=seed, trace_i=trace_i, event_ordinal=ev["ordinal"],
            iteration=ev["ordinal"],
            spec_i=s, trans_i=float(transf[i]),
            sign_i=int(np.sign(round(s * 6 * 3))),  # spec_i*18 is integer-exact on the lattice
            tie_delta_share=z(deltas), tie_delta_own_share=z(d_own), tie_delta_other_share=z(d_oth),
            tie_margin_share=z(margs),
            n_deltas=len(deltas), n_margins=len(margs),
            accept=int(ev["accept"]),
        ))
    # corpus-wide reproduction from the per-event table (weighted means; equal N per event)
    w_delta = float(np.mean([r["tie_delta_share"] for r in out_rows]))
    w_marg = float(np.mean([r["tie_margin_share"] for r in out_rows]))
    check("part1.delta_all_from_events", f"{w_delta:.4f}", EXPECT["ties"]["delta_all"])
    check("part1.margin_all_from_events", f"{w_marg:.4f}", EXPECT["ties"]["margin_all"])
    zero_spec = sum(1 for r in out_rows if r["sign_i"] == 0)
    print(f"events: {len(out_rows)}; sign_i: +{sum(1 for r in out_rows if r['sign_i']>0)} "
          f"/ 0:{zero_spec} / -{sum(1 for r in out_rows if r['sign_i']<0)}; "
          f"accepts: {sum(r['accept'] for r in out_rows)}")
    if fails:
        print("STOP — per-event table does not reproduce corpus-wide tie shares.")
        sys.exit(1)

    cols = list(out_rows[0].keys())
    with open(os.path.join(OUTDIR, "outcomes.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(out_rows)
    print(f"[wrote {os.path.join(OUTDIR, 'outcomes.csv')}]  ({len(out_rows)} rows)")


if __name__ == "__main__":
    main()
