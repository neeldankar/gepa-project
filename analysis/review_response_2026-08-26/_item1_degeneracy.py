"""Item 1: realized §15-12 degeneracy on the LIVE runs, beside the design-time dose.json.

$0, read-only. Every statistic computed twice by independent code paths, asserted to 1e-12.
"""
import hashlib, itertools, json, math, os, statistics as st
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RUNS = os.path.join(REPO, "analysis", "state_dep", "runs")
DOSE = os.path.join(REPO, "analysis", "state_dep", "dose.json")
OUT = os.path.join(HERE, "01_degeneracy_realized.md")
SEEDS, M, B = tuple(range(8)), 6, 3

# dose_compute.py:74-77 -- the screen's within-run SD of knn_emb_fb_min. Same normalizer the
# design-time estimate used, so realized and design-time numbers are directly comparable.
SD_PER_SEED = {0: 0.02186988, 1: 0.02443303, 2: 0.02946035, 3: 0.02319585,
               4: 0.02871316, 5: 0.02523783, 6: 0.02501051, 7: 0.02653783}


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def spread_np(x6):
    a = np.sort(np.asarray(x6, float))
    return {"sd": float(np.std(a, ddof=1)), "range": float(a[-1] - a[0]),
            "t3b3": float(a[M - B:].mean() - a[:B].mean()),
            "sel_min": float(a[M - B]),
            "exp_rand_min": float(np.mean([min(s) for s in itertools.combinations(a.tolist(), B)]))}


def spread_py(x6):
    a = sorted(float(v) for v in x6)
    return {"sd": st.stdev(a), "range": a[-1] - a[0],
            "t3b3": sum(a[M - B:]) / B - sum(a[:B]) / B,
            "sel_min": a[M - B],
            "exp_rand_min": sum(min(s) for s in itertools.combinations(a, B)) / 20.0}


def summ_np(v):
    a = np.asarray(v, float)
    return {"n": int(a.size), "mean": float(a.mean()), "sd": float(a.std(ddof=1)),
            "min": float(a.min()), "p25": float(np.percentile(a, 25)),
            "median": float(np.median(a)), "p75": float(np.percentile(a, 75)), "max": float(a.max())}


def summ_py(v):
    a = sorted(float(x) for x in v); n = len(a)
    def pct(q):
        pos = q / 100 * (n - 1); lo = int(pos); hi = min(lo + 1, n - 1)
        return a[lo] + (a[hi] - a[lo]) * (pos - lo)
    return {"n": n, "mean": sum(a) / n, "sd": st.stdev(a), "min": a[0], "p25": pct(25),
            "median": pct(50), "p75": pct(75), "max": a[-1]}


def agree(d1, d2, tag):
    for k, v in d1.items():
        if isinstance(v, float) and abs(v - d2[k]) > 1e-12:
            raise SystemExit(f"FAIL second path {tag}.{k}: {v!r} vs {d2[k]!r}")
    return d1


rows, excl = {"T": [], "C": []}, {"T": {}, "C": {}}
for arm in ("B", "C", "T"):
    for s in SEEDS:
        p = os.path.join(RUNS, f"{arm}_seed{s}", "event_log.json")
        if not os.path.exists(p):
            continue
        for e in json.load(open(p)):
            nv = e.get("novelties")
            if arm == "B" or nv is None:
                excl.setdefault(arm, {}); excl[arm]["no_novelty_field"] = excl[arm].get("no_novelty_field", 0) + 1
                continue
            if len(nv) != M or any(v is None or (isinstance(v, float) and math.isnan(v)) for v in nv):
                key = "coldstart_archive_lt_3" if e.get("archive_size_at_scoring", 9) < 3 else "nan_other"
                excl[arm][key] = excl[arm].get(key, 0) + 1
                continue
            r = agree(spread_np(nv), spread_py(nv), f"{arm}_s{s}")
            r.update(arm=arm, seed=s, sdn=r["sd"] / SD_PER_SEED[s], rgn=r["range"] / SD_PER_SEED[s],
                     t3n=r["t3b3"] / SD_PER_SEED[s], gap=r["sel_min"] - r["exp_rand_min"],
                     gapn=(r["sel_min"] - r["exp_rand_min"]) / SD_PER_SEED[s],
                     rule=e.get("rule"))
            rows[arm].append(r)

MET = [("sd", "SD of the 6"), ("range", "range (max minus min)"), ("t3b3", "top3 minus bottom3 mean"),
       ("sdn", "SD / within-run SD"), ("rgn", "range / within-run SD"),
       ("t3n", "(top3 minus bottom3) / within-run SD"), ("gap", "selected_min minus E[random-3 min]"),
       ("gapn", "that gap / within-run SD")]

dose = json.load(open(DOSE))
dz = [v["x6"] for v in dose["per_event"].values()]
drows = []
for pid, v in dose["per_event"].items():
    sd_s = SD_PER_SEED[int(pid.split("_")[0].replace("seed", ""))]
    r = agree(spread_np(v["x6"]), spread_py(v["x6"]), f"dose_{pid}")
    r.update(t3n=r["t3b3"] / sd_s, rgn=r["range"] / sd_s, sdn=r["sd"] / sd_s,
             gap=r["sel_min"] - r["exp_rand_min"], gapn=(r["sel_min"] - r["exp_rand_min"]) / sd_s)
    drows.append(r)

L = []
w = L.append
w("# Item 1: which corpus is the degeneracy check computed on")
w("")
w("Numbers only. No interpretation.")
w("")
w("## Finding")
w("")
w("`dose.json`'s 235 events are **(b), the pre-experiment corpus**, not the live runs.")
w("")
w("| evidence | value |")
w("|---|---|")
w("| `dose_compute.py:48` | `SCREEN = analysis/hover_screen` |")
w("| `dose_compute.py:232` | enumerates events from `SCREEN/events_index.json` |")
w("| `events_index.json` | 243 entries, mtime 2026-07-09, keys `{seed, trace_i, ordinal, idx, subsample_ids, accept, ...}` |")
w("| `dose_acquire.py:50-52` | texts resolved from `analysis/ablation/hover_swap/pairs` (243 pair dirs) |")
w("| 243 minus 8 ordinal-0 events with no k=3 archive | **235** |")
w("| live experiment reflection events | 645 across 24 runs; 187 in arm T |")
w("")
w("The realized live novelty scores WERE persisted, in `runs/<arm>_seed<n>/event_log.json` as a")
w("per-event `novelties` 6-vector. The realized distribution is computed below.")
w("")
w("## Events available")
w("")
w("| arm | events in log | usable (complete non-NaN 6-vector) | excluded |")
w("|---|---|---|---|")
for arm in ("B", "C", "T"):
    tot = len(rows.get(arm, [])) + sum(excl.get(arm, {}).values())
    ex = ", ".join(f"{k} {v}" for k, v in sorted(excl.get(arm, {}).items())) or "none"
    w(f"| {arm} | {tot} | {len(rows.get(arm, []))} | {ex} |")
w("")
w("Arm B draws 3 examples directly and has no 6-candidate step, so no novelty vector exists for it.")
w("")
w("## Realized spread, live runs")
w("")
for arm in ("T", "C"):
    w(f"### Arm {arm} ({len(rows[arm])} events)")
    w("")
    w("| statistic | n | mean | SD | min | p25 | median | p75 | max |")
    w("|---|---|---|---|---|---|---|---|---|")
    for k, nm in MET:
        d = agree(summ_np([r[k] for r in rows[arm]]), summ_py([r[k] for r in rows[arm]]), f"{arm}{k}")
        w(f"| {nm} | {d['n']} | {d['mean']:.6f} | {d['sd']:.6f} | {d['min']:.6f} | {d['p25']:.6f} "
          f"| {d['median']:.6f} | {d['p75']:.6f} | {d['max']:.6f} |")
    w("")
    z1 = sum(1 for r in rows[arm] if r["range"] == 0.0)
    z2 = sum(1 for r in rows[arm] if r["t3b3"] == 0.0)
    w(f"Exact zeros: range == 0 in **{z1}/{len(rows[arm])}**; top3 minus bottom3 == 0 in "
      f"**{z2}/{len(rows[arm])}**.")
    w("")
    w("Per seed, (top3 minus bottom3) / within-run SD:")
    w("")
    w("| seed | n | mean | SD | min | median | max |")
    w("|---|---|---|---|---|---|---|")
    for s in SEEDS:
        v = [r["t3n"] for r in rows[arm] if r["seed"] == s]
        if not v:
            w(f"| {s} | 0 | - | - | - | - | - |"); continue
        d = agree(summ_np(v), summ_py(v), f"{arm}s{s}")
        w(f"| {s} | {d['n']} | {d['mean']:.6f} | {d['sd']:.6f} | {d['min']:.6f} | {d['median']:.6f} "
          f"| {d['max']:.6f} |")
    w("")

w("## Design-time (dose.json, 235 events) beside realized arm T")
w("")
w("| statistic | dose.json median | dose.json min | arm T median | arm T min |")
w("|---|---|---|---|---|")
for k, nm in MET:
    dd = agree(summ_np([r[k] for r in drows]), summ_py([r[k] for r in drows]), f"dose{k}")
    tt = agree(summ_np([r[k] for r in rows["T"]]), summ_py([r[k] for r in rows["T"]]), f"T{k}")
    w(f"| {nm} | {dd['median']:.6f} | {dd['min']:.6f} | {tt['median']:.6f} | {tt['min']:.6f} |")
w("")
w("## Provenance")
w("")
w("| field | value |")
w("|---|---|")
w(f"| dose.json sha256 | `{sha(DOSE)}` |")
w(f"| dose.json events | {len(drows)} |")
w(f"| live arm-T events used | {len(rows['T'])} |")
w(f"| live arm-C events used | {len(rows['C'])} |")
w(f"| normalizer | SD_PER_SEED, dose_compute.py:74-77 |")
w("")
w("Every statistic above computed twice (numpy vs pure Python) and asserted to 1e-12.")
w("")
open(OUT, "w").write("\n".join(L) + "\n")
print(f"wrote {os.path.basename(OUT)}")
print(f"  arm T usable {len(rows['T'])}, arm C usable {len(rows['C'])}, dose {len(drows)}")
for arm in ("T", "C"):
    d = summ_np([r["t3n"] for r in rows[arm]])
    print(f"  arm {arm} (top3-bottom3)/SD: median {d['median']:.4f} min {d['min']:.4f} max {d['max']:.4f}")
dd = summ_np([r["t3n"] for r in drows])
print(f"  dose      (top3-bottom3)/SD: median {dd['median']:.4f} min {dd['min']:.4f} max {dd['max']:.4f}")
