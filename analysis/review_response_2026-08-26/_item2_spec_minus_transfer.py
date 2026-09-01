"""Item 2: paired specificity minus transfer on the HoVer swap corpus. $0, read-only.

Reuses load(), thirds(), draw_avg(), perm_p() and cluster_boot() from hover_swap_analysis.py
unchanged, at its constants NPERM = NBOOT = 20000, Z80 = 2.802, K = 3. The per-pair specificity and
transfer expressions are copied verbatim from that module's main() (:131-132).

Every headline statistic recomputed by an independent path and asserted to 1e-12.
"""
import collections, hashlib, importlib.util, os, statistics as st
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
os.chdir(REPO)                                   # module resolves OUT/PAIRS relatively
SRC = "analysis/ablation/hover_swap/hover_swap_analysis.py"
OUT = os.path.join(HERE, "02_specificity_minus_transfer.md")

spec_ = importlib.util.spec_from_file_location("hsa", SRC)
m = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(m)

rows = m.load()
by_pair = collections.defaultdict(list)
for r in rows:
    by_pair[r["pair"]].append(r)

spec, transf, clusters, pids = [], [], [], []
for pid, rs in sorted(by_pair.items()):
    a_sa = m.draw_avg(rs, "SAME", "margin_on_A"); a_sw = m.draw_avg(rs, "SWAP", "margin_on_A")
    b_sa = m.draw_avg(rs, "SAME", "margin_on_B"); b_sw = m.draw_avg(rs, "SWAP", "margin_on_B")
    if np.any(np.isnan([a_sa, a_sw, b_sa, b_sw])):
        continue
    spec.append((((a_sa - a_sw) + (b_sw - b_sa)) / 2) / 3.0)
    transf.append(((b_sa + a_sw) / 2) / 3.0)
    clusters.append(rs[0]["seed"]); pids.append(pid)
spec, transf, clusters = np.array(spec), np.array(transf), np.array(clusters)
d = spec - transf

# ---- path 1: the module's own machinery, verbatim -----------------------------------------
m.rng = np.random.default_rng(20260703)          # reset so the two calls are reproducible
obs1, p1 = m.perm_p(d)
m.rng = np.random.default_rng(20260703)
lo1, hi1, se1 = m.cluster_boot(d, clusters)
mde1 = m.Z80 * se1

# ---- path 2: independent implementation ----------------------------------------------------
mean2 = sum(float(x) for x in d) / len(d)
rng2 = np.random.default_rng(20260703)
null2 = np.array([float(np.mean(np.asarray(d) * rng2.choice([-1.0, 1.0], len(d))))
                  for _ in range(m.NPERM)])
p2 = float(np.mean(np.abs(null2) >= abs(mean2) - 1e-12))
rng2b = np.random.default_rng(20260703)
uniq = sorted(set(clusters.tolist()))
by = {c: [float(v) for v, cl in zip(d, clusters) if cl == c] for c in uniq}
mm = []
for _ in range(m.NBOOT):
    pick = rng2b.choice(np.array(uniq), len(uniq), replace=True)
    pool = [v for c in pick for v in by[c]]
    mm.append(sum(pool) / len(pool))
mm_s = sorted(mm); n = len(mm_s)
def pct(q):
    pos = q / 100 * (n - 1); lo = int(pos); hi = min(lo + 1, n - 1)
    return mm_s[lo] + (mm_s[hi] - mm_s[lo]) * (pos - lo)
lo2, hi2, se2 = pct(2.5), pct(97.5), st.stdev(mm)

for nm, a, b in (("mean", float(obs1), mean2), ("perm p", p1, p2), ("CI lo", lo1, lo2),
                 ("CI hi", hi1, hi2), ("SE", se1, se2)):
    if abs(a - b) > 1e-12:
        raise SystemExit(f"FAIL second path {nm}: {a!r} vs {b!r}")

pos = int((d > 0).sum()); neg = int((d < 0).sum())
per_seed = collections.Counter(clusters.tolist())

L = []; w = L.append
w("# Item 2: paired specificity minus transfer, HoVer swap corpus")
w("")
w("Numbers only. No interpretation.")
w("")
w(f"Per-pair `d = specificity - transfer` over {len(d)} pairs, 8 run clusters, K = {m.K} draws per")
w("arm. Machinery reused unchanged from `hover_swap_analysis.py`: `load()`, `draw_avg()`,")
w(f"`perm_p()` (within-pair sign-flip, NPERM = {m.NPERM}), `cluster_boot()` (run-level cluster")
w(f"bootstrap over seeds, NBOOT = {m.NBOOT}), MDE = Z80 x SE with Z80 = {m.Z80}.")
w("")
w("## Result")
w("")
w("| estimand | point | 95% CI (run cluster-boot) | SE (clustered) | MDE | perm p (within-pair) |")
w("|---|---|---|---|---|---|")
w(f"| specificity minus transfer | {float(obs1):+.9f} | [{lo1:+.6f}, {hi1:+.6f}] | {se1:.6f} | {mde1:.6f} | {p1:.6f} |")
w("")
w("Reference, recomputed here from the same rows:")
w("")
w("| estimand | point |")
w("|---|---|")
w(f"| pooled specificity | {float(np.mean(spec)):+.9f} |")
w(f"| pooled transfer | {float(np.mean(transf)):+.9f} |")
w(f"| difference | {float(np.mean(spec)) - float(np.mean(transf)):+.9f} |")
w("")
w(f"Sign split on the {len(d)} per-pair differences: {pos} positive, {neg} negative, "
  f"{len(d)-pos-neg} exactly zero.")
w("")
w("## Per seed")
w("")
w("| seed | pairs | mean d | SD |")
w("|---|---|---|---|")
for c in uniq:
    v = by[c]
    w(f"| {c} | {per_seed[c]} | {sum(v)/len(v):+.6f} | {st.stdev(v):.6f} |")
w("")
w("## Provenance")
w("")
w("| field | value |")
w("|---|---|")
w(f"| pairs | {len(d)} |")
w(f"| draw rows | {len(rows)} |")
w(f"| hover_swap_analysis.py sha256 | `{hashlib.sha256(open(SRC,'rb').read()).hexdigest()}` |")
w("")
w("Mean, permutation p, CI bounds and SE each computed twice by independent implementations and")
w("asserted to 1e-12.")
w("")
open(OUT, "w").write("\n".join(L) + "\n")
print(f"wrote {os.path.basename(OUT)}")
print(f"  pairs={len(d)}  spec-transf={float(obs1):+.6f}  CI=[{lo1:+.6f},{hi1:+.6f}]  "
      f"SE={se1:.6f}  MDE={mde1:.6f}  p={p1:.6f}")
print(f"  spec={float(np.mean(spec)):+.6f}  transf={float(np.mean(transf)):+.6f}  "
      f"signs {pos}+/{neg}-")
