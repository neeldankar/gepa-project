"""Item 3: emit the permutation calibration report from _perm_raw.json. $0, read-only."""
import csv, hashlib, json, os, statistics as st
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCREEN = os.path.join(REPO, "analysis", "hover_screen")
RAW = os.path.join(HERE, "_perm_raw.json")
OUT = os.path.join(HERE, "03_permutation_calibration.md")

raw = json.load(open(RAW))
raw = {int(k): v for k, v in raw.items()}
perms = sorted(k for k in raw if k > 0)
cells = sorted(raw[0]["cells"])


def crit_a(rec, c, lm):
    r = rec[c]["41"]
    return (r["lo"] == r["lo"] and (r["lo"] > 0 or r["hi"] < 0) and r["loro"] >= lm and r["p"] < 0.05)


def crit_b(rec, c, lm):
    r = rec[c]["42"]
    return (crit_a(rec, c, lm) and r["lo"] == r["lo"] and (r["lo"] > 0 or r["hi"] < 0)
            and r["p"] < 0.05)


def surv(p, lm):
    rec = raw[p]["cells"]; mcb = set(raw[p]["mcb"])
    a = [c for c in cells if crit_a(rec, c, lm)]
    b = [c for c in cells if crit_b(rec, c, lm)]
    return a, b, [c for c in a if c in mcb], [c for c in b if c in mcb]


# ---- published reference + identity validation ------------------------------------------
R = {}
for r in csv.DictReader(open(os.path.join(SCREEN, "screen_stats_cells.csv"))):
    R[(r["cell"], r["outcome"], r["read"])] = r
pub_beta = float(R[("knn_emb_fb_min", "spec_i", "4.1")]["beta"])
ia, ib, iam, ibm = surv(0, 7)
PUB_A = ["knn_emb_fb_min", "knn_emb_full_max", "knn_emb_full_mean"]
PUB_B = ["knn_emb_fb_min", "knn_emb_full_mean"]
val_a, val_b = sorted(ia) == PUB_A, sorted(ib) == PUB_B

L = []; w = L.append
w("# Item 3: permutation calibration of the 108-cell conjunction rule")
w("")
w("Numbers only. No interpretation.")
w("")
w("## What was permuted")
w("")
w("The outcome `spec_i` is permuted **within seed**, holding all 108 scorers fixed. This preserves")
w("the cross-cell correlation structure, which is what makes a maximum over 108 cells a valid null.")
w("Mirrors the negative-control construction at `screen_part4_stats.py:23-30`.")
w("")
w(f"Permutations: **{len(perms)}** plus one identity pass. Full original fidelity, B = P = 9999,")
w("`CellEngine`, `perrun_z` and `bca_ci` reused unchanged.")
w("")
w("## The rule, as implemented")
w("")
w("From `screen_part4_stats.py:277-284`, verbatim in effect:")
w("")
w("- **crit_a**: BCa CI on read 4.1 excludes 0, **LORO >= 7** (not 8), permutation p < 0.05.")
w("- **crit_b**: crit_a AND read 4.2 CI excludes 0 AND read 4.2 p < 0.05. It chains crit_a and does")
w("  not re-check LORO on 4.2.")
w("- **MCB** (`:289-297`): a cell is retained if the 5th percentile of")
w("  `max_others |beta_boot| - |beta_boot|` is <= 0, over shared bootstrap draws.")
w("")
w("## Identity-pass validation")
w("")
w("| predicate | identity pass | published `screen_stats_cells.csv` | reproduces |")
w("|---|---|---|---|")
w(f"| crit_a | {len(ia)}: {sorted(ia)} | {len(PUB_A)}: {PUB_A} | {'YES' if val_a else 'NO'} |")
w(f"| crit_b | {len(ib)}: {sorted(ib)} | {len(PUB_B)}: {PUB_B} | {'YES' if val_b else 'NO'} |")
w(f"| crit_b + MCB | {len(ibm)}: {sorted(ibm)} | published sole survivor: `knn_emb_fb_min` | "
  f"{'YES' if sorted(ibm) == ['knn_emb_fb_min'] else 'NO'} |")
w("")
w("The stated conjunction rule alone leaves 3 cells under crit_a and 2 under crit_b. The published")
w("single-survivor status of `knn_emb_fb_min` is reached only after the MCB step.")
w("")

if not (val_a and val_b):
    w("**VALIDATION FAILED. The calibration below is not emitted.**")
    open(OUT, "w").write("\n".join(L) + "\n")
    raise SystemExit("identity pass did not reproduce the published survivor set")

w("## Calibration")
w("")
w("Fraction of permutations yielding at least one survivor, by predicate and LORO threshold:")
w("")
w("| predicate | LORO >= 7 | LORO == 8 |")
w("|---|---|---|")
res = {}
for lm in (7, 8):
    for i, nm in enumerate(("crit_a", "crit_b", "crit_a + MCB", "crit_b + MCB")):
        res[(nm, lm)] = [len(surv(p, lm)[i]) for p in perms]
for nm in ("crit_a", "crit_b", "crit_a + MCB", "crit_b + MCB"):
    f7 = sum(1 for v in res[(nm, 7)] if v > 0) / len(perms)
    f8 = sum(1 for v in res[(nm, 8)] if v > 0) / len(perms)
    w(f"| {nm} | {f7:.4f} ({sum(1 for v in res[(nm,7)] if v>0)}/{len(perms)}) | "
      f"{f8:.4f} ({sum(1 for v in res[(nm,8)] if v>0)}/{len(perms)}) |")
w("")
w("Survivor-count distribution under the null (LORO >= 7):")
w("")
w("| predicate | mean | max | 0 survivors | 1 | 2 | 3 or more |")
w("|---|---|---|---|---|---|---|")
for nm in ("crit_a", "crit_b", "crit_a + MCB", "crit_b + MCB"):
    v = res[(nm, 7)]
    w(f"| {nm} | {sum(v)/len(v):.4f} | {max(v)} | {sum(1 for x in v if x==0)} "
      f"| {sum(1 for x in v if x==1)} | {sum(1 for x in v if x==2)} "
      f"| {sum(1 for x in v if x>=3)} |")
w("")
w("## Null distribution of the maximum beta across the 108 cells")
w("")
mx = [raw[p]["max_beta"] for p in perms]
ma = [raw[p]["max_abs_beta"] for p in perms]
w("| statistic | mean | SD | p50 | p90 | p95 | p99 | max |")
w("|---|---|---|---|---|---|---|---|")
for nm, v in (("max beta", mx), ("max |beta|", ma)):
    a = np.asarray(v)
    w(f"| {nm} | {a.mean():.6f} | {a.std(ddof=1):.6f} | {np.percentile(a,50):.6f} "
      f"| {np.percentile(a,90):.6f} | {np.percentile(a,95):.6f} | {np.percentile(a,99):.6f} "
      f"| {a.max():.6f} |")
w("")
obs_mx = raw[0]["max_beta"]
w(f"Observed `knn_emb_fb_min` beta on read 4.1: **{pub_beta:+.6f}**. Observed max beta across the")
w(f"108 cells on unpermuted data: **{obs_mx:+.6f}**.")
w("")
w("| comparison | value |")
w("|---|---|")
w(f"| permutations with max beta >= observed max | {sum(1 for v in mx if v >= obs_mx - 1e-12)}/{len(perms)} "
  f"= {sum(1 for v in mx if v >= obs_mx - 1e-12)/len(perms):.4f} |")
w(f"| permutations with max beta >= {pub_beta:.5f} | {sum(1 for v in mx if v >= pub_beta - 1e-12)}/{len(perms)} "
  f"= {sum(1 for v in mx if v >= pub_beta - 1e-12)/len(perms):.4f} |")
w("")
w("## Provenance")
w("")
w("| field | value |")
w("|---|---|")
w(f"| permutations (excluding identity) | {len(perms)} |")
w(f"| cells per race | {len(cells)} |")
w(f"| B (bootstrap), P (within-run permutation) | 9999, 9999 |")
w(f"| screen_part4_stats.py sha256 | `{hashlib.sha256(open(os.path.join(SCREEN,'screen_part4_stats.py'),'rb').read()).hexdigest()}` |")
w(f"| features.csv sha256 | `{hashlib.sha256(open(os.path.join(SCREEN,'features.csv'),'rb').read()).hexdigest()}` |")
w(f"| outcomes.csv sha256 | `{hashlib.sha256(open(os.path.join(SCREEN,'outcomes.csv'),'rb').read()).hexdigest()}` |")
w("")
open(OUT, "w").write("\n".join(L) + "\n")
print(f"wrote {os.path.basename(OUT)}")
print(f"  identity validation: crit_a {val_a}, crit_b {val_b}, crit_b+MCB {sorted(ibm)}")
for nm in ("crit_a", "crit_b", "crit_b + MCB"):
    f7 = sum(1 for v in res[(nm, 7)] if v > 0) / len(perms)
    print(f"  {nm:16} >=1 survivor in {f7:.4f} of permutations")
print(f"  max-beta null: p95 {np.percentile(mx,95):.5f}, observed max {obs_mx:.5f}")
