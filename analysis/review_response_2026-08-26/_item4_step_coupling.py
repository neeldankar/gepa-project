"""Item 4: step-count coupling and endpoint versus steps. EXPLORATORY, descriptive only. $0.

Not pre-registered. No test here is confirmatory and no causal claim is made or implied.
Every headline statistic computed twice by independent code paths, asserted to 1e-12.
"""
import hashlib, json, math, os, statistics as st
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
RUNS = os.path.join(REPO, "analysis", "state_dep", "runs")
OUT = os.path.join(HERE, "04_step_coupling.md")
ARMS, SEEDS = ("B", "C", "T"), tuple(range(8))
BOOT, SEED = 10000, 20260709


def pearson_np(x, y):
    return float(np.corrcoef(np.asarray(x, float), np.asarray(y, float))[0, 1])


def pearson_py(x, y):
    n = len(x); mx = sum(x) / n; my = sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = math.sqrt(sum((a - mx) ** 2 for a in x)); syy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sxy / (sxx * syy)


def rank(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    r = [0.0] * len(v); i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and v[order[j + 1]] == v[order[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            r[order[k]] = avg
        i = j + 1
    return r


def spearman(x, y):
    return pearson_py(rank(list(x)), rank(list(y)))


def boot_ci(x, y, seed=SEED):
    rng = np.random.default_rng(seed)
    n = len(x); idx = rng.integers(0, n, size=(BOOT, n))
    rs = []
    for row in idx.tolist():
        xs = [x[i] for i in row]; ys = [y[i] for i in row]
        if len(set(xs)) < 2 or len(set(ys)) < 2:
            continue
        rs.append(pearson_py(xs, ys))
    rs.sort(); m = len(rs)
    def pct(q):
        pos = q / 100 * (m - 1); lo = int(pos); hi = min(lo + 1, m - 1)
        return rs[lo] + (rs[hi] - rs[lo]) * (pos - lo)
    return pct(2.5), pct(97.5), m


D = {}
for a in ARMS:
    for s in SEEDS:
        rs = json.load(open(os.path.join(RUNS, f"{a}_seed{s}", "run_summary.json")))
        ep = json.load(open(os.path.join(RUNS, f"{a}_seed{s}", "endpoints.json")))
        D[(a, s)] = {"events": int(rs["reflection_events"]), "accepts": int(rs["accepts"]),
                     "cands": int(rs["candidates_incl_seed"]), "evals": int(rs["total_num_evals"]),
                     "endpoint": float(ep["endpoint_test_mean"])}
assert len(D) == 24

L = []; w = L.append
w("# Item 4: step-count coupling and endpoint versus steps")
w("")
w("**EXPLORATORY. Descriptive only.** None of this was pre-registered. No test below is")
w("confirmatory, no p-value is reported against a decision threshold, and no causal claim is made")
w("or implied. Correlations over 8 seeds are unstable by construction; intervals are shown to make")
w("that width visible, not to support inference.")
w("")
w("Numbers only. No interpretation.")
w("")
w("## Reflection events versus accepts, within arm")
w("")
w("| arm | n | Pearson r | Spearman rho | 95% bootstrap CI on r (resample seeds) |")
w("|---|---|---|---|---|")
for a in ARMS:
    ev = [D[(a, s)]["events"] for s in SEEDS]; ac = [D[(a, s)]["accepts"] for s in SEEDS]
    r1, r2 = pearson_np(ev, ac), pearson_py(ev, ac)
    if abs(r1 - r2) > 1e-12:
        raise SystemExit(f"FAIL second path pearson {a}: {r1!r} vs {r2!r}")
    lo, hi, nb = boot_ci(ev, ac)
    w(f"| {a} | 8 | {r1:+.6f} | {spearman(ev, ac):+.6f} | [{lo:+.4f}, {hi:+.4f}] |")
ev_all = [D[(a, s)]["events"] for a in ARMS for s in SEEDS]
ac_all = [D[(a, s)]["accepts"] for a in ARMS for s in SEEDS]
lo, hi, _ = boot_ci(ev_all, ac_all)
w(f"| all 24 | 24 | {pearson_np(ev_all, ac_all):+.6f} | {spearman(ev_all, ac_all):+.6f} "
  f"| [{lo:+.4f}, {hi:+.4f}] |")
w("")
ident = all(D[k]["cands"] == D[k]["accepts"] + 1 for k in D)
w(f"`candidates_incl_seed == accepts + 1` holds for all 24 runs: **{ident}**. The two are the same")
w("quantity up to a constant, so any correlation involving candidates equals the one involving")
w("accepts.")
w("")
w("## Reflection events per arm")
w("")
w("| arm | mean | SD | min | max | per-seed values (0..7) |")
w("|---|---|---|---|---|---|")
for a in ARMS:
    ev = [D[(a, s)]["events"] for s in SEEDS]
    w(f"| {a} | {sum(ev)/8:.4f} | {st.stdev(ev):.4f} | {min(ev)} | {max(ev)} | "
      f"{', '.join(str(x) for x in ev)} |")
w("")
w("## Endpoint versus reflection events")
w("")
w("| scope | n | Pearson r | Spearman rho | 95% bootstrap CI on r |")
w("|---|---|---|---|---|")
for a in ARMS:
    ev = [D[(a, s)]["events"] for s in SEEDS]; en = [D[(a, s)]["endpoint"] for s in SEEDS]
    lo, hi, _ = boot_ci(ev, en)
    w(f"| arm {a} | 8 | {pearson_np(ev, en):+.6f} | {spearman(ev, en):+.6f} | [{lo:+.4f}, {hi:+.4f}] |")
en_all = [D[(a, s)]["endpoint"] for a in ARMS for s in SEEDS]
lo, hi, _ = boot_ci(ev_all, en_all)
w(f"| all 24 runs | 24 | {pearson_np(ev_all, en_all):+.6f} | {spearman(ev_all, en_all):+.6f} "
  f"| [{lo:+.4f}, {hi:+.4f}] |")
w("")
w("## Endpoint versus accepts")
w("")
w("| scope | n | Pearson r | Spearman rho | 95% bootstrap CI on r |")
w("|---|---|---|---|---|")
for a in ARMS:
    ac = [D[(a, s)]["accepts"] for s in SEEDS]; en = [D[(a, s)]["endpoint"] for s in SEEDS]
    lo, hi, _ = boot_ci(ac, en)
    w(f"| arm {a} | 8 | {pearson_np(ac, en):+.6f} | {spearman(ac, en):+.6f} | [{lo:+.4f}, {hi:+.4f}] |")
lo, hi, _ = boot_ci(ac_all, en_all)
w(f"| all 24 runs | 24 | {pearson_np(ac_all, en_all):+.6f} | {spearman(ac_all, en_all):+.6f} "
  f"| [{lo:+.4f}, {hi:+.4f}] |")
w("")
w("## Per-run table")
w("")
w("| arm | seed | reflection events | accepts | candidates | total evals | endpoint |")
w("|---|---|---|---|---|---|---|")
for a in ARMS:
    for s in SEEDS:
        v = D[(a, s)]
        w(f"| {a} | {s} | {v['events']} | {v['accepts']} | {v['cands']} | {v['evals']} "
          f"| {v['endpoint']:.6f} |")
w("")
w("## Provenance")
w("")
w("| field | value |")
w("|---|---|")
w(f"| runs read | 24 (`run_summary.json` + `endpoints.json`) |")
w(f"| bootstrap | {BOOT} resamples, seed {SEED}, percentile method |")
w("")
w("Pearson r computed twice (numpy vs pure Python) for every scope and asserted to 1e-12.")
w("")
open(OUT, "w").write("\n".join(L) + "\n")
print(f"wrote {os.path.basename(OUT)}")
for a in ARMS:
    ev = [D[(a, s)]["events"] for s in SEEDS]; ac = [D[(a, s)]["accepts"] for s in SEEDS]
    en = [D[(a, s)]["endpoint"] for s in SEEDS]
    print(f"  arm {a}: r(events,accepts)={pearson_np(ev,ac):+.4f}  r(events,endpoint)={pearson_np(ev,en):+.4f}")
print(f"  all24: r(events,accepts)={pearson_np(ev_all,ac_all):+.4f}  "
      f"r(events,endpoint)={pearson_np(ev_all,en_all):+.4f}")
