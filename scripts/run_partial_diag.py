"""Partial-cell diagnosis (Step 4) — read-only, no API.

Is partial->full conversion benign (unsampled) or adversarial (constraint tradeoff)?
Part A: which constraint stays unsatisfied (concentration + failure rate + flip consistency).
Part B: does fixing one constraint break another (parent->child tradeoff test + trajectory).
Per-constraint data is minibatch/trainset-scoped only (valset stores scalars) — stated below.

    .venv/bin/python scripts/run_partial_diag.py
"""

from __future__ import annotations

import os

import pandas as pd

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.partial_diag import (
    constraint_type, flip_consistency, tradeoff_stats, trajectory, unsatisfied_on_partial,
)

OUT_PARQUET = "analysis/partial_diag.parquet"


def main() -> None:
    runs = load_corpus()
    n_cyc = sum(len(r.cycles) for r in runs)
    n_after = sum(1 for r in runs for c in r.cycles if c.child_objscores is not None)
    print(f"loaded {len(runs)} runs, {n_cyc} reflection cycles "
          f"({n_after} with a child/after eval for the tradeoff test)\n")
    print("LIMITATION: per-constraint satisfaction is logged at the MINIBATCH (trainset) level "
          "only;\n  valset stores scalar fractions. Parts A/B describe reflection on its INPUT "
          "examples,\n  not the 150 valset cells (same dataset distribution, so structure "
          "transfers).\n")

    pd.set_option("display.width", 170, "display.max_columns", 30)

    # ---- Part A1 ----
    a1 = unsatisfied_on_partial(runs)
    print("=" * 78)
    print(f"[A1] unsatisfied constraints on PARTIAL minibatch cells "
          f"({a1['n_partial_cells']} partial of {a1['n_cells']} cells, "
          f"{a1['n_types_seen']}/16 types)")
    print(f"  top-3-type share of all unsatisfied-on-partial: {a1['top3_share']:.1%}  "
          f"(spread => benign; concentrated => structural)")
    a1df = pd.DataFrame(a1["rows"])
    print(a1df.round(3).to_string(index=False))

    # ---- Part A2 ----
    a2 = flip_consistency(runs)
    print("\n" + "=" * 78)
    print(f"[A2] flip consistency (trainset proxy for Step-3 swingable; valset version impossible)")
    print(f"  (example,constraint) pairs seen >=2x: {a2['n_pairs_multiseen']}  | "
          f"flipping (both pass & fail observed): {a2['n_flipping']}  | "
          f"top-3-type share of flips: {a2['top3_flip_share']:.1%}")
    print(pd.DataFrame(a2["rows"]).round(3).to_string(index=False))

    # ---- Part B3 ----
    print("\n" + "=" * 78)
    print("[B3] tradeoff test — parent->child per-constraint on the SAME minibatch cell")
    for accepted_only in (True, False):
        b = tradeoff_stats(runs, accepted_only=accepted_only)
        print(f"\n  scope={b['scope']}  ({b['n_cells']} cells)")
        print(f"    improvements (0->1): {b['n_improve']}   regressions (1->0): {b['n_regress']}   "
              f"regress/improve = {b['regress_per_improve']:.3f}")
        print(f"    cells improving >=1 constraint: {b['n_cells_with_improve']}; of those, "
              f"ALSO regressing >=1 (SMOKING GUN): {b['n_coregress']} "
              f"({b['coregress_frac_of_improving']:.1%})")
        print(f"    per-step Δsat: mean={b['delta_mean']:.3f} median={b['delta_median']:.1f} "
              f"frac_neg={b['delta_frac_neg']:.1%} frac_pos={b['delta_frac_pos']:.1%}")
        if b["top_pairs"]:
            pairs = "  ".join(f"{iu}↑/{rd}↓:{n}" for (iu, rd), n in b["top_pairs"][:6])
            print(f"    top (improved↑ / regressed↓) type pairs: {pairs}")

    # ---- Part B4 ----
    tr = trajectory(runs)
    print("\n" + "=" * 78)
    print(f"[B4] within-example trajectory (trainset examples sampled >=2x, NOT already full; sparse)")
    tot = max(tr["n_series"], 1)
    print(f"  not-already-full series: {tr['n_series']}  (excluded {tr['n_already_full']} always-full)")
    print(f"    reached full (benign):      {tr['reached_full']} ({tr['reached_full']/tot:.0%})")
    print(f"    climbing, not yet full:     {tr['climbed_not_full']} ({tr['climbed_not_full']/tot:.0%})")
    print(f"    FLAT-STUCK (never moves):   {tr['flat_stuck']} ({tr['flat_stuck']/tot:.0%})")
    print(f"    oscillate:                  {tr['oscillate']} ({tr['oscillate']/tot:.0%})")

    # ---- verdict ----
    bw = tradeoff_stats(runs, accepted_only=False)
    co = bw["coregress_frac_of_improving"]
    print("\n" + "=" * 78)
    print("VERDICT")
    print(f"  A1 top-3 type share={a1['top3_share']:.0%} | "
          f"B3 co-regression (of improving cells)={co:.0%} | "
          f"regress/improve={bw['regress_per_improve']:.2f} | "
          f"Δsat frac_neg={bw['delta_frac_neg']:.0%}")
    benign_a = a1["top3_share"] <= 0.55
    benign_b = co <= 0.20 and bw["regress_per_improve"] <= 0.35
    if benign_a and benign_b:
        print("  => BENIGN / unsampled: failures spread across types, fixes accumulate with few "
              "co-regressions. Partial cells are reachable; a curriculum could land them. Lever alive.")
    elif (not benign_a) and (not benign_b):
        print("  => ADVERSARIAL / tradeoff: failures concentrated AND fixing one constraint "
              "frequently breaks another. Per-example selection won't move this; favor "
              "proposal-shaping / Direction-C.")
    else:
        print("  => MIXED: benign on part of the constraint space, adversarial on the rest. The "
              "low-failure-rate + low-co-regression subset is the realistic lever ceiling "
              "(see A1 fail_rate columns + B3 pairs to size it).")

    # ---- artifact ----
    rows = []
    for r in runs:
        for c in r.cycles:
            if c.child_objscores is None:
                continue
            for ex_i, (pex, cex) in enumerate(zip(c.parent_objscores, c.child_objscores)):
                for k in set(pex) & set(cex):
                    rows.append({
                        "run": f"s{r.seed}_b{r.b}", "iter": c.iteration, "example_pos": ex_i,
                        "constraint": k.split("#", 1)[0], "type": constraint_type(k),
                        "parent_sat": int(pex[k] == 1.0), "child_sat": int(cex[k] == 1.0),
                        "accepted": bool(c.accept),
                    })
    df = pd.DataFrame(rows)
    os.makedirs("analysis", exist_ok=True)
    df.to_parquet(OUT_PARQUET, index=False)
    print(f"\nwrote {OUT_PARQUET}: {df.shape[0]} rows x {df.shape[1]} cols")


if __name__ == "__main__":
    main()
