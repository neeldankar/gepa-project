"""Emit analysis/state_dep/degeneracy_descriptive.md: numbers only, no interpretation.

$0. No LM calls, no network. Read-only over dose.json and runs/*/run_summary.json.

Two design-required descriptives that had never been computed:

  §15-12  selection-pressure degeneracy. "If realized novelty scores are near-constant across the
          6 (nothing to select on), T ~= C by construction and the experiment measures nothing."
          §9's (null,null) cell: "Consult the degeneracy descriptive (§15-12) before any 'signal
          does not transfer' reading." §11-0 (:740-742) names the statistics: "the per-event
          novelty spread (max-min and SD of the 6) as the §15-12 degeneracy pre-estimate; and, for
          free, the expected T-vs-C choice overlap."

  §15-4   monitored descriptives, no tests: reflection events/run, accept rate/arm, candidates/run.
          §3 (R9): H1 is "strictly a **policy** contrast, not a mechanism contrast ... Mechanism
          attribution leans on the monitored descriptives; see §15-4."

NO NUMERIC CRITERION IS INVENTED. §15-12 says "near-constant" and states no threshold; this file
reports the distribution and says so. The only degeneracy count reported is spread == 0 exactly,
which is unambiguous and needs no threshold. Spreads are additionally normalized by SD_PER_SEED --
the design's own unit, since beta is "per within-run SD" (§11-1) -- so the numbers are readable
against the scale the design already uses, not against a bar this script made up.

Every statistic is computed twice by independent code paths and asserted to 1e-12.

  .venv-armT/bin/python analysis/state_dep/emit_descriptives.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import itertools
import json
import os
import statistics as st

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
DOSE = os.path.join(HERE, "dose.json")
OUT = os.path.join(HERE, "degeneracy_descriptive.md")

ARMS = ("B", "C", "T")
SEEDS = tuple(range(8))
M, B_PICK = 6, 3

# dose_compute.py:74-77 -- the screen's within-run SD of knn_emb_fb_min, per seed. beta is expressed
# per one of these units (§11-1), so normalizing by it puts spread on the design's own scale.
SD_PER_SEED = {
    0: 0.02186988, 1: 0.02443303, 2: 0.02946035, 3: 0.02319585,
    4: 0.02871316, 5: 0.02523783, 6: 0.02501051, 7: 0.02653783,
}

CRITERION_QUOTE = (
    "12. **Selection-pressure degeneracy.** If realized novelty scores are near-constant across "
    "the\n    6 (nothing to select on), T ≈ C by construction and the experiment measures "
    "nothing.\n    Monitored: per-event novelty spread and T-vs-C choice overlap (§8). "
    "§11-0 converts this from\n    monitor-only into a **pre-spend estimate**. A (null,null) "
    "read must check this descriptive\n    before concluding \"signal doesn't transfer\"."
)


# ------------------------------------------------------------------ per-event spread, two paths
def spread_numpy(x6):
    a = np.sort(np.asarray(x6, dtype=float))
    return {
        "sd": float(np.std(a, ddof=1)),
        "range": float(a[-1] - a[0]),
        "top3_bottom3": float(a[M - B_PICK:].mean() - a[:B_PICK].mean()),
    }


def spread_python(x6):
    a = sorted(float(v) for v in x6)
    return {
        "sd": st.stdev(a),
        "range": a[-1] - a[0],
        "top3_bottom3": (sum(a[M - B_PICK:]) / B_PICK) - (sum(a[:B_PICK]) / B_PICK),
    }


def summarize_numpy(v):
    a = np.asarray(v, dtype=float)
    return {"n": int(a.size), "mean": float(a.mean()), "sd": float(a.std(ddof=1)),
            "min": float(a.min()), "p25": float(np.percentile(a, 25)),
            "median": float(np.median(a)), "p75": float(np.percentile(a, 75)),
            "max": float(a.max())}


def summarize_python(v):
    a = sorted(float(x) for x in v)
    n = len(a)

    def pct(q):
        pos = q / 100.0 * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        return a[lo] + (a[hi] - a[lo]) * (pos - lo)

    return {"n": n, "mean": sum(a) / n, "sd": st.stdev(a), "min": a[0], "p25": pct(25),
            "median": pct(50), "p75": pct(75), "max": a[-1]}


def agree(d1, d2, tag):
    for k in d1:
        if isinstance(d1[k], (int, float)) and abs(d1[k] - d2[k]) > 1e-12:
            raise SystemExit(f"FAIL second-path {tag}.{k}: {d1[k]!r} vs {d2[k]!r}")
    return d1


def expected_overlap_exact() -> tuple[float, float]:
    """|top3 ∩ random-3-of-6| averaged over all C(6,3)=20 subsets, and the same by hypergeometric
    mean 3*3/6. Structural constant of pick-3-of-6, independent of the data."""
    top = {0, 1, 2}
    ov = [len(top & set(s)) for s in itertools.combinations(range(6), 3)]
    if len(ov) != 20:
        raise SystemExit(f"FAIL: {len(ov)} subsets, expected 20")
    return float(np.mean(ov)), B_PICK * B_PICK / M


def main() -> int:
    # ---------------------------------------------------------------- §15-12
    dose = json.load(open(DOSE))
    per_event = dose["per_event"]
    if len(per_event) != 235:
        raise SystemExit(f"FAIL: dose.json per_event has {len(per_event)}, expected 235")

    rows, by_seed = [], {s: [] for s in SEEDS}
    for pid, rec in per_event.items():
        seed = int(pid.split("_")[0].replace("seed", ""))
        x6 = rec["x6"]
        if len(x6) != M:
            raise SystemExit(f"FAIL {pid}: x6 has {len(x6)}, expected {M}")
        sp = agree(spread_numpy(x6), spread_python(x6), f"spread[{pid}]")
        sp.update(pid=pid, seed=seed, gap=rec["gap"], n_arch=rec["n_arch"],
                  sd_norm=sp["sd"] / SD_PER_SEED[seed],
                  range_norm=sp["range"] / SD_PER_SEED[seed],
                  t3b3_norm=sp["top3_bottom3"] / SD_PER_SEED[seed])
        rows.append(sp)
        by_seed[seed].append(sp)
    if len(rows) != 235:
        raise SystemExit(f"FAIL: {len(rows)} events summarized, expected 235")

    metrics = ("sd", "range", "top3_bottom3", "sd_norm", "range_norm", "t3b3_norm")
    overall = {m: agree(summarize_numpy([r[m] for r in rows]),
                        summarize_python([r[m] for r in rows]), f"summary[{m}]")
               for m in metrics}
    per_seed_sum = {s: {m: agree(summarize_numpy([r[m] for r in by_seed[s]]),
                                 summarize_python([r[m] for r in by_seed[s]]), f"seed{s}[{m}]")
                        for m in metrics} for s in SEEDS}

    n_zero_range = sum(1 for r in rows if r["range"] == 0.0)
    n_zero_t3b3 = sum(1 for r in rows if r["top3_bottom3"] == 0.0)
    ov_enum, ov_hyper = expected_overlap_exact()
    if abs(ov_enum - ov_hyper) > 1e-12:
        raise SystemExit(f"FAIL overlap: {ov_enum!r} vs {ov_hyper!r}")

    # ---------------------------------------------------------------- §15-4
    mon = {}
    for arm in ARMS:
        for s in SEEDS:
            p = os.path.join(RUNS, f"{arm}_seed{s}", "run_summary.json")
            if not os.path.exists(p):
                raise SystemExit(f"FAIL: missing {p}")
            r = json.load(open(p))
            if r["arm"] != arm or int(r["seed"]) != s:
                raise SystemExit(f"FAIL {p}: arm/seed mismatch {r['arm']}/{r['seed']}")
            ev = int(r["reflection_events"])
            ac = int(r["accepts"])
            mon[(arm, s)] = {
                "reflection_events": ev, "accepts": ac,
                "child_bearing_events": int(r["child_bearing_events"]),
                "candidates_incl_seed": int(r["candidates_incl_seed"]),
                "total_num_evals": int(r["total_num_evals"]),
                "accept_rate": ac / ev,
            }
    if len(mon) != 24:
        raise SystemExit(f"FAIL: {len(mon)} run summaries, expected 24")

    mon_metrics = ("accept_rate", "reflection_events", "candidates_incl_seed", "accepts",
                   "total_num_evals")
    arm_sum = {a: {m: agree(summarize_numpy([mon[(a, s)][m] for s in SEEDS]),
                            summarize_python([mon[(a, s)][m] for s in SEEDS]), f"{a}[{m}]")
                   for m in mon_metrics} for a in ARMS}

    # ---------------------------------------------------------------- write
    L = []
    w = L.append
    w("# state-dependent — §15-12 degeneracy and §15-4 monitored descriptives")
    w("")
    w("Numbers only. No interpretation, no verdicts, no grid-cell assignment.")
    w(f"Emitted by `emit_descriptives.py` from `dose.json` ({len(rows)} events) and "
      f"{len(mon)} `run_summary.json`.")
    w("")
    w("---")
    w("")
    w("## §15-12 — selection-pressure degeneracy")
    w("")
    w("### The criterion, verbatim (design v2 §15, item 12)")
    w("")
    w("> " + CRITERION_QUOTE.replace("\n", "\n> "))
    w("")
    w("**§15-12 states no numeric threshold.** It says \"near-constant\" and names the statistics to")
    w("monitor; it does not define a cutoff separating degenerate from non-degenerate events. No")
    w("threshold is invented here. The distributions below are reported in full; the only counts")
    w("given are exact zeros, which require no threshold.")
    w("")
    w("Statistics are those §11-0 (`:740-742`) names as the degeneracy pre-estimate: per-event")
    w("novelty spread as **max−min** and **SD of the 6**, plus the **top-3 − bottom-3 mean gap**.")
    w("`*_norm` divides by that seed's within-run SD (`dose_compute.py:74-77`), the unit β is")
    w("expressed in (§11-1).")
    w("")
    w("### Across all 235 events")
    w("")
    w("| statistic | n | mean | SD | min | p25 | median | p75 | max |")
    w("|---|---|---|---|---|---|---|---|---|")
    names = {"sd": "SD of the 6", "range": "range (max−min)", "top3_bottom3": "top3 − bottom3 mean",
             "sd_norm": "SD / within-run SD", "range_norm": "range / within-run SD",
             "t3b3_norm": "(top3 − bottom3) / within-run SD"}
    for m in metrics:
        d = overall[m]
        w(f"| {names[m]} | {d['n']} | {d['mean']:.6f} | {d['sd']:.6f} | {d['min']:.6f} | "
          f"{d['p25']:.6f} | {d['median']:.6f} | {d['p75']:.6f} | {d['max']:.6f} |")
    w("")
    w("### Exact-zero counts (threshold-free)")
    w("")
    w("| quantity | events | of | fraction |")
    w("|---|---|---|---|")
    w(f"| range (max−min) == 0 exactly | {n_zero_range} | {len(rows)} | {n_zero_range / len(rows):.6f} |")
    w(f"| top3 − bottom3 == 0 exactly | {n_zero_t3b3} | {len(rows)} | {n_zero_t3b3 / len(rows):.6f} |")
    w("")
    w("### Per seed")
    w("")
    for m in ("range", "top3_bottom3", "t3b3_norm"):
        w(f"**{names[m]}**")
        w("")
        w("| seed | n | mean | SD | min | median | max |")
        w("|---|---|---|---|---|---|---|")
        for s in SEEDS:
            d = per_seed_sum[s][m]
            w(f"| {s} | {d['n']} | {d['mean']:.6f} | {d['sd']:.6f} | {d['min']:.6f} | "
              f"{d['median']:.6f} | {d['max']:.6f} |")
        w("")
    w("### T-vs-C choice overlap (structural constant, not measured)")
    w("")
    w("| quantity | value |")
    w("|---|---|")
    w(f"| E[ \\|top-3 ∩ random-3\\| ] over all C(6,3)=20 subsets | {ov_enum:.6f} |")
    w(f"| hypergeometric mean 3·3/6 | {ov_hyper:.6f} |")
    w(f"| implied expected disjoint picks per event | {B_PICK - ov_enum:.6f} of {B_PICK} |")
    w("")
    w("This is a property of pick-3-of-6, identical in every arm and event; it does not depend on")
    w("the novelty scores and is reported because §11-0 lists it as an output.")
    w("")
    w("---")
    w("")
    w("## §15-4 — monitored descriptives (no tests)")
    w("")
    w("`accept_rate` = `accepts` / `reflection_events` from each run's `run_summary.json`.")
    w("")
    w("### Per-arm means over the 8 seeds")
    w("")
    w("| arm | accept rate | reflection events | candidates (incl. seed) | accepts | total evals |")
    w("|---|---|---|---|---|---|")
    for a in ARMS:
        d = arm_sum[a]
        w(f"| {a} | {d['accept_rate']['mean']:.6f} | {d['reflection_events']['mean']:.4f} | "
          f"{d['candidates_incl_seed']['mean']:.4f} | {d['accepts']['mean']:.4f} | "
          f"{d['total_num_evals']['mean']:.4f} |")
    w("")
    w("### Per-arm SD over the 8 seeds")
    w("")
    w("| arm | accept rate | reflection events | candidates (incl. seed) |")
    w("|---|---|---|---|")
    for a in ARMS:
        d = arm_sum[a]
        w(f"| {a} | {d['accept_rate']['sd']:.6f} | {d['reflection_events']['sd']:.4f} | "
          f"{d['candidates_incl_seed']['sd']:.4f} |")
    w("")
    w("### Per seed, per arm")
    w("")
    w("| arm | seed | reflection events | child-bearing events | accepts | accept rate | "
      "candidates (incl. seed) | total evals |")
    w("|---|---|---|---|---|---|---|---|")
    for a in ARMS:
        for s in SEEDS:
            d = mon[(a, s)]
            w(f"| {a} | {s} | {d['reflection_events']} | {d['child_bearing_events']} | "
              f"{d['accepts']} | {d['accept_rate']:.6f} | {d['candidates_incl_seed']} | "
              f"{d['total_num_evals']} |")
    w("")
    w("---")
    w("")
    w("## Provenance")
    w("")
    w("| field | value |")
    w("|---|---|")
    w(f"| events (dose.json per_event) | {len(rows)} |")
    w(f"| run summaries read | {len(mon)} |")
    w(f"| dose.json sha256 | `{hashlib.sha256(open(DOSE, 'rb').read()).hexdigest()}` |")
    w(f"| emit_descriptives.py sha256 | `{hashlib.sha256(open(__file__, 'rb').read()).hexdigest()}` |")
    w(f"| emitted | {dt.datetime.now().isoformat(timespec='seconds')} |")
    w("")
    w("### verification performed before emission")
    w("")
    w(f"- {len(rows)} events, each with exactly 6 novelty scores")
    w(f"- {len(mon)} run summaries, arm/seed field matching directory name, 8 per arm")
    w("- every per-event spread computed twice (numpy vs pure Python), |delta| <= 1e-12")
    w("- every summary computed twice (numpy vs pure Python), |delta| <= 1e-12")
    w("- expected overlap by exact 20-subset enumeration vs hypergeometric mean, |delta| <= 1e-12")
    w("")

    with open(OUT, "w") as fh:
        fh.write("\n".join(L) + "\n")

    print(f"wrote {os.path.relpath(OUT, HERE)}")
    print(f"  events               : {len(rows)}")
    print(f"  run summaries        : {len(mon)}")
    print(f"  exact-zero range     : {n_zero_range}/{len(rows)}")
    print(f"  exact-zero top3-bot3 : {n_zero_t3b3}/{len(rows)}")
    print("  second-path checks   : all passed (<=1e-12)")
    print()
    print("  --- §15-12 spread, all 235 events ---")
    for m in metrics:
        d = overall[m]
        print(f"    {names[m]:<32} median {d['median']:.6f}  mean {d['mean']:.6f}  "
              f"min {d['min']:.6f}  max {d['max']:.6f}")
    print()
    print("  --- §15-4 per-arm means ---")
    for a in ARMS:
        d = arm_sum[a]
        print(f"    arm {a}: accept_rate {d['accept_rate']['mean']:.6f}  "
              f"events {d['reflection_events']['mean']:.4f}  "
              f"candidates {d['candidates_incl_seed']['mean']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
