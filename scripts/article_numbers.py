"""Article number register: recompute every number the blog draft needs from raw committed files ($0).

Read-only on everything that exists. Writes only analysis/article_numbers/*.csv (compute) and
analysis/article_numbers/fig_*.{png,svg} (figures). No API calls, no model calls.

  analysis/state_dep/.venv-armT/bin/python -B scripts/article_numbers.py compute
  <throwaway venv with matplotlib>/bin/python -B scripts/article_numbers.py figures

`compute` needs only stdlib + numpy (the armT venv; Python 3.12). `figures` reads only the CSVs that
`compute` wrote. Run both from the repo root.

Every value goes through rec(): it is printed beside its reference (if any) with MATCH/MISMATCH and
written to values.csv with its tag ([R] stated in a committed artifact and reproduced here; [C] new),
the raw file it was computed from, the committed doc that states it, and the producing function.
A reference given as a decimal string is matched to half a unit of its last printed digit; bootstrap
CI bounds quoted as "about" use an explicit Monte-Carlo tolerance, printed in the row.
"""
from __future__ import annotations

import argparse
import ast
import collections
import csv
import glob
import hashlib
import importlib.util
import itertools
import json
import math
import os
import re
import subprocess
import sys
from fractions import Fraction

OUT = "analysis/article_numbers"
NBOOT = 10000
SEED0 = 20261015                     # bootstrap CI k uses default_rng(SEED0 + k), k fixed per CI
MC_TOL = 0.005                       # tolerance for "about" bootstrap CI bounds (Monte-Carlo noise)
IFB = "analysis/ablation/batch_swap_v2/calls.csv"
HOVER_PAIRS = "analysis/ablation/hover_swap/pairs"
PERM = "analysis/review_response_2026-08-26/_perm_raw.json"
SD_RUNS = "analysis/state_dep/runs"
FRONTIER = os.path.expanduser(os.environ.get("FRONTIER_GEPA", "~/Desktop/frontier-gepa"))

VALUES = []


def _tol_from(ref: str) -> float:
    s = ref.lstrip("+-")
    return 0.5 * 10 ** -(len(s.split(".")[1])) if "." in s else 0.0


def rec(id_, value, ref=None, *, tol=None, tag="[C]", raw="", cited="", note=""):
    """Record one value. ref: str (decimal as printed in the reference), int, or None."""
    fn = sys._getframe(1).f_code.co_name
    status = ""
    if ref is not None:
        if isinstance(value, str) or isinstance(ref, (list, tuple)):
            status = "MATCH" if value == ref else "MISMATCH"
        elif isinstance(ref, int) and not isinstance(ref, bool):
            status = "MATCH" if value == ref else "MISMATCH"
        else:
            t = _tol_from(ref) if tol is None else tol
            status = "MATCH" if abs(float(value) - float(ref)) <= t + 1e-12 else "MISMATCH"
            if tol is not None:
                note = (note + f"; tol={tol}").lstrip("; ")
    v = value if isinstance(value, (str, int)) else repr(float(value))
    VALUES.append(dict(id=id_, value=v, ref="" if ref is None else str(ref), status=status, tag=tag,
                       raw=raw, cited=cited, fn=fn, note=note))
    print(f"  {id_:<44} {str(v):<24} ref={'' if ref is None else ref!s:<14} {status:<9} {tag} {note}")
    return value


def write_csv(name, rows, fields=None):
    path = os.path.join(OUT, name)
    fields = fields or list(rows[0].keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------- shared statistics

def kappa_from_sums(n, sa, sb, sab):
    """Cohen's kappa for two binary verdicts from aggregate counts (works on numpy arrays)."""
    po = (n - sa - sb + 2 * sab) / n
    pa, pb = sa / n, sb / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return (po - pe) / (1 - pe), po, pe


def boot_kappa_ci(a, b, clusters, k):
    """Percentile 95% CI for kappa, resampling whole clusters with replacement (NBOOT draws)."""
    import numpy as np
    rng = np.random.default_rng(SEED0 + k)
    a, b = np.asarray(a, int), np.asarray(b, int)
    ids = {c: i for i, c in enumerate(sorted(set(clusters)))}
    ci = np.array([ids[c] for c in clusters])
    G = len(ids)
    M = np.zeros((G, 4))
    np.add.at(M, ci, np.stack([np.ones_like(a), a, b, a * b], axis=1))
    ks = []
    for start in range(0, NBOOT, 500):
        m = min(500, NBOOT - start)
        idx = rng.integers(0, G, size=(m, G))
        S = M[idx].sum(axis=1)
        ks.append(kappa_from_sums(S[:, 0], S[:, 1], S[:, 2], S[:, 3])[0])
    ks = np.concatenate(ks)
    return float(np.percentile(ks, 2.5)), float(np.percentile(ks, 97.5)), G


def two_by_two(a, b):
    c = collections.Counter(zip(a, b))
    return c[(True, True)], c[(True, False)], c[(False, True)], c[(False, False)]


def exact_mean(xs):
    """article_todos Appendix:304-309, verbatim: exact rational mean of k/d scores, d <= 5."""
    fs = [Fraction(x).limit_denominator(1000) for x in xs]
    assert all(abs(float(f) - x) < 1e-12 and f.denominator <= 5 for f, x in zip(fs, xs))
    return sum(fs) / len(fs)


def signflip_exact(d):
    """Exact two-sided sign-flip p over all 2^n patterns: share with |mean| >= |obs| - 1e-12."""
    n = len(d)
    obs = sum(d) / n
    hits = sum(abs(sum(s * x for s, x in zip(sg, d)) / n) >= abs(obs) - 1e-12
               for sg in itertools.product((1, -1), repeat=n))
    return obs, hits / 2 ** n


def _betacf(a, b, x):
    """Continued fraction for the regularized incomplete beta (Numerical Recipes betacf, modified Lentz)."""
    tiny, qab, qap, qam = 1e-300, a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 1000):
        m2 = 2 * m
        for aa in (m * (b - m) * x / ((qam + m2) * (a + m2)), -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))):
            d = 1.0 + aa * d
            d = 1.0 / (d if abs(d) > tiny else tiny)
            c = 1.0 + aa / c
            c = c if abs(c) > tiny else tiny
            h *= d * c
        if abs(d * c - 1.0) < 1e-15:
            return h
    raise RuntimeError("betacf did not converge")


def betai(a, b, x):
    """Regularized incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(lbt) * _betacf(a, b, x) / a
    return 1.0 - math.exp(lbt) * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    """Student-t CDF (df may be fractional), stdlib only; tested against scipy in tests/test_t_dist.py."""
    tail = 0.5 * betai(df / 2.0, 0.5, df / (df + t * t))
    return 1.0 - tail if t >= 0 else tail


def t_ppf(p, df):
    """Student-t quantile by bisection on t_cdf (to 1e-12)."""
    lo, hi = -1e3, 1e3
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if t_cdf(mid, df) < p else (lo, mid)
        if hi - lo < 1e-12:
            break
    return (lo + hi) / 2


def load_module(name, path):
    sp = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(m)
    return m


def git(*args, cwd=FRONTIER):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True).stdout


# ---------------------------------------------------------------- Part A: IFBench batch-swap v2

def load_ifb():
    rows = list(csv.DictReader(open(IFB)))
    assert len(rows) == 2292
    for r in rows:
        for k in ("child_sum_B", "child_sum_Bp", "parent_B_sum", "parent_Bp_sum", "margin_on_B", "margin_on_Bp"):
            r[k] = float(r[k])
        own_B = r["arm"] == "R_B"
        r["own_m"], r["oth_m"] = (r["margin_on_B"], r["margin_on_Bp"]) if own_B else (r["margin_on_Bp"], r["margin_on_B"])
        r["own_p"], r["oth_p"] = (r["parent_B_sum"], r["parent_Bp_sum"]) if own_B else (r["parent_Bp_sum"], r["parent_B_sum"])
        r["run"] = r["B_id"].split("_")[0]
    cells = collections.Counter((r["B_id"], r["arm"]) for r in rows)
    assert len({r["B_id"] for r in rows}) == 382 and set(cells.values()) == {3} and len(cells) == 764
    return rows


def a0_arm_semantics():
    src = open("scripts/batch_swap_v2_run.py").read().splitlines()
    l220, l221, l223 = src[219], src[220], src[222]
    ok = ("objs_B = parent_eval(pkey, P, B_ids)" in l220 and "R_B reflects on B" in l220
          and "objs_Bp = parent_eval(pkey, P, Bp_ids)" in l221 and "R_B' reflects on B'" in l221
          and '"R_B": build_prompt(P, objs_B), "R_Bp": build_prompt(P, objs_Bp)' in l223)
    rec("A0.arm_R_B_reflects_on_B_and_R_Bp_on_Bprime", "confirmed" if ok else "NOT CONFIRMED", "confirmed",
        tag="[R]", raw="scripts/batch_swap_v2_run.py:220-223",
        cited="scripts/batch_swap_v2_run.py:220-221 (inline comments)")


def a1_opening(rows):
    r = rows[0]
    rec("A1.row1_ids", f"{r['B_id']}/{r['Bprime_id']}/{r['arm']}/draw{r['draw']}", "s4_it63/s4_it47/R_Bp/draw0",
        tag="[R]", raw=f"{IFB}:2")
    rec("A1.row1_child_on_B", r["child_sum_B"], "1.0", tag="[R]", raw=f"{IFB}:2")
    rec("A1.row1_parent_on_B", r["parent_B_sum"], "0.75", tag="[R]", raw=f"{IFB}:2")
    rec("A1.row1_verdict_on_B", "keep" if r["margin_on_B"] > 0 else "reject", "keep", tag="[R]", raw=f"{IFB}:2")
    rec("A1.row1_child_on_Bp", r["child_sum_Bp"], "1.0833", tag="[R]", raw=f"{IFB}:2")
    rec("A1.row1_parent_on_Bp", r["parent_Bp_sum"], "1.3333", tag="[R]", raw=f"{IFB}:2")
    rec("A1.row1_verdict_on_Bp", "keep" if r["margin_on_Bp"] > 0 else "reject", "reject", tag="[R]", raw=f"{IFB}:2")
    rec("A1.row1_written_from", "B' (arm R_Bp reflects on B')" if r["arm"] == "R_Bp" else "B", tag="[C]",
        raw=f"{IFB}:2; scripts/batch_swap_v2_run.py:221,223",
        note="rejected on the batch it was written from; kept only on the other batch")
    rec("A1.row1_own_batch_verdict", "keep" if r["own_m"] > 0 else "reject", tag="[C]", raw=f"{IFB}:2")


def a2_cross_batch(rows):
    a = [r["margin_on_B"] > 0 for r in rows]
    b = [r["margin_on_Bp"] > 0 for r in rows]
    tt, tf, ft, ff = two_by_two(a, b)
    raw = IFB
    cited = "analysis/article_todos_2026-10-08.md:81"
    rec("A2.n_children", len(rows), 2292, tag="[R]", raw=raw, cited=cited)
    rec("A2.2x2_acc_acc", tt, 272, tag="[R]", raw=raw, cited=cited)
    rec("A2.2x2_acc_rej", tf, 468, tag="[R]", raw=raw, cited=cited)
    rec("A2.2x2_rej_acc", ft, 588, tag="[R]", raw=raw, cited=cited)
    rec("A2.2x2_rej_rej", ff, 964, tag="[R]", raw=raw, cited=cited)
    n = len(rows)
    k, po, pe = kappa_from_sums(n, sum(a), sum(b), tt)
    rec("A2.agreement", po, "0.5393", tag="[R]", raw=raw, cited=cited)
    rec("A2.accept_rate_on_B", sum(a) / n, tag="[C]", raw=raw)
    rec("A2.accept_rate_on_Bp", sum(b) / n, tag="[C]", raw=raw)
    rec("A2.chance_agreement", pe, "0.5442", tag="[C]", raw=raw, note="pa*pb+(1-pa)(1-pb) from the 2x2 marginals")
    rec("A2.kappa", k, "-0.0108", tag="[C]", raw=raw)
    for j, (unit, cl) in enumerate([("children", list(range(n))), ("pairs_B_id", [r["B_id"] for r in rows]),
                                    ("runs_seed_prefix", [r["run"] for r in rows])]):
        lo, hi, G = boot_kappa_ci(a, b, cl, k=j)
        refs = {"children": ("-0.052", "+0.030"), "pairs_B_id": ("-0.061", "+0.040"),
                "runs_seed_prefix": ("-0.046", "+0.040")}[unit]
        rec(f"A2.kappa_ci95_lo_resample_{unit}", lo, refs[0], tol=MC_TOL, tag="[C]", raw=raw,
            note=f"percentile, {NBOOT} resamples of {G} clusters, rng {SEED0 + j}")
        rec(f"A2.kappa_ci95_hi_resample_{unit}", hi, refs[1], tol=MC_TOL, tag="[C]", raw=raw,
            note=f"percentile, {NBOOT} resamples of {G} clusters, rng {SEED0 + j}")
    return dict(obs=po, chance=pe, n=n, kappa=k)


def _siblings(rows, field):
    cells = collections.defaultdict(list)
    for r in rows:
        cells[(r["B_id"], r["arm"])].append(r[field] > 0)
    pair_ag, nonunan = [], 0
    for v in cells.values():
        pair_ag.append(sum(x == y for x, y in itertools.combinations(v, 2)) / 3)
        nonunan += len(set(v)) != 1
    p = sum(r[field] > 0 for r in rows) / len(rows)
    return sum(pair_ag) / len(pair_ag), p * p + (1 - p) ** 2, p, nonunan / len(cells), len(cells)


def a3_siblings(rows):
    raw = IFB
    obs, ch, p, u, nc = _siblings(rows, "own_m")
    rec("A3.sibling_cells", nc, 764, tag="[R]", raw=raw, cited="analysis/verification_postswap.md:9")
    rec("A3.sibling_agreement_own_batch", obs, "0.7234", tag="[C]", raw=raw)
    rec("A3.own_batch_accept_rate_pooled", p, "0.3442", tag="[R]", raw=raw, cited="analysis/verification_postswap.md:13")
    rec("A3.sibling_chance_own_batch", ch, "0.5485", tag="[C]", raw=raw, note="p^2+(1-p)^2, p pooled own-batch accept")
    rec("A3.nonunanimous_cell_share_own", u, "0.4149", tag="[R]", raw=raw, cited="analysis/verification_postswap.md:51")
    rec("A3.identity_1_minus_2/3_x_0.4149", 1 - (2 / 3) * 0.4149, "0.7234", tag="[C]",
        note="3 draws: unanimous cell agrees 3/3 pairs, 2-1 cell 1/3; so mean = 1-(2/3)*share non-unanimous")
    rec("A3.identity_exact_on_recomputed_share", abs(obs - (1 - (2 / 3) * u)) < 1e-12 and "exact" or "FAILS", "exact",
        tag="[C]")
    rec("A3.identity_chance_from_0.3442", 0.3442 ** 2 + 0.6558 ** 2, "0.5485", tag="[C]")
    obs2, ch2, p2, u2, _ = _siblings(rows, "oth_m")
    rec("A3.sibling_agreement_other_batch", obs2, "0.7251", tag="[C]", raw=raw)
    rec("A3.other_batch_accept_rate_pooled", p2, tag="[C]", raw=raw)
    rec("A3.sibling_chance_other_batch", ch2, "0.5427", tag="[C]", raw=raw)
    return dict(obs=obs, chance=ch, n=nc)


def a4_ties(rows):
    raw = IFB
    rec("A4.zero_margin_on_B", sum(r["margin_on_B"] == 0 for r in rows), 838, tag="[R]", raw=raw,
        cited="analysis/article_todos_2026-10-08.md:94")
    rec("A4.zero_margin_on_Bp", sum(r["margin_on_Bp"] == 0 for r in rows), 677, tag="[R]", raw=raw,
        cited="analysis/article_todos_2026-10-08.md:94")
    rec("A4.zero_margin_on_own_batch", sum(r["own_m"] == 0 for r in rows), 769, tag="[C]", raw=raw)
    nz = [abs(r[k]) for r in rows for k in ("margin_on_B", "margin_on_Bp") if r[k] != 0]
    rec("A4.smallest_nonzero_abs_margin", min(nz), "0.0333", tag="[R]", raw=raw,
        cited="analysis/article_todos_2026-10-08.md:95")


BINS = [(0.0, 0.5), (0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, 2.5), (2.5, 3.0)]


def _bin(x):
    assert 0 <= x <= 3.0 + 1e-9, x
    return min(int(x / 0.5 + 1e-12), 5)


def a5_headroom(rows):
    own = collections.defaultdict(lambda: [0, 0])
    allv = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        b = _bin(r["own_p"]); own[b][0] += 1; own[b][1] += r["own_m"] > 0
        for p, m in ((r["parent_B_sum"], r["margin_on_B"]), (r["parent_Bp_sum"], r["margin_on_Bp"])):
            b = _bin(p); allv[b][0] += 1; allv[b][1] += m > 0
    assert sum(v[0] for v in own.values()) == 2292 and sum(v[0] for v in allv.values()) == 4584
    out = []
    for i, (lo, hi) in enumerate(BINS):
        lab = f"[{lo},{hi})" if i < 5 else f"[{lo},{hi}]"
        n_o, k_o = own[i]; n_a, k_a = allv[i]
        out.append(dict(bin=lab, lo=lo, hi=hi, n_own=n_o, kept_own=k_o, keep_rate_own=round(k_o / n_o, 6) if n_o else "",
                        n_all=n_a, kept_all=k_a, keep_rate_all=round(k_a / n_a, 6) if n_a else ""))
        rec(f"A5.own_{lab}_n", n_o, tag="[C]", raw=IFB)
        rec(f"A5.own_{lab}_keep", k_o / n_o if n_o else float("nan"), tag="[C]", raw=IFB)
        ref_n = {0: 180, 5: 246}.get(i)
        ref_k = {0: "0.728", 5: "0.073"}.get(i)
        rec(f"A5.all_{lab}_n", n_a, ref_n, tag="[C]", raw=IFB)
        rec(f"A5.all_{lab}_keep", k_a / n_a if n_a else float("nan"), ref_k, tag="[C]", raw=IFB)
    write_csv("fig_gate_headroom.csv", out)


# ---------------------------------------------------------------- Part B: HoVer swap

def load_hover():
    m = load_module("hs", "analysis/ablation/hover_swap/hover_swap_analysis.py")
    rows = m.load()                                    # asserts 243 pairs x 6, margins in integer thirds
    meta = {p: json.load(open(f"{HOVER_PAIRS}/{p}/meta.json")) for p in {r["pair"] for r in rows}}
    for r in rows:
        assert meta[r["pair"]]["seed"] == r["seed"]
        r["match_exact"] = meta[r["pair"]]["match_exact"]
    return m, rows


def b_hover(m, rows):
    raw = f"{HOVER_PAIRS}/*/draws.jsonl, meta.json"
    a = [r["margin_on_A"] > 0 for r in rows]
    b = [r["margin_on_B"] > 0 for r in rows]
    n = len(rows)
    rec("B1.n_children", n, 1458, tag="[R]", raw=raw, cited="analysis/article_todos_2026-10-08.md:82")
    tt, tf, ft, ff = two_by_two(a, b)
    for nm, v, ref in (("acc_acc", tt, 184), ("acc_rej", tf, 334), ("rej_acc", ft, 327), ("rej_rej", ff, 613)):
        rec(f"B1.2x2_{nm}", v, ref, tag="[R]", raw=raw, cited="analysis/article_todos_2026-10-08.md:82")
    k, po, pe = kappa_from_sums(n, sum(a), sum(b), tt)
    rec("B1.agreement", po, "0.5466", tag="[R]", raw=raw, cited="analysis/article_todos_2026-10-08.md:82")
    rec("B1.chance_agreement", pe, "0.5433", tag="[C]", raw=raw)
    rec("B1.kappa", k, "0.007", tag="[C]", raw=raw)
    for j, (unit, cl, rl, rh) in enumerate([("pairs", [r["pair"] for r in rows], "-0.057", "+0.070"),
                                            ("seeds", [r["seed"] for r in rows], "-0.055", "+0.059")]):
        lo, hi, G = boot_kappa_ci(a, b, cl, k=10 + j)
        rec(f"B1.kappa_ci95_lo_resample_{unit}", lo, rl, tol=MC_TOL, tag="[C]", raw=raw,
            note=f"percentile, {NBOOT} resamples of {G} clusters, rng {SEED0 + 10 + j}")
        rec(f"B1.kappa_ci95_hi_resample_{unit}", hi, rh, tol=MC_TOL, tag="[C]", raw=raw,
            note=f"percentile, {NBOOT} resamples of {G} clusters, rng {SEED0 + 10 + j}")
    # B2: split by meta.json match_exact
    for flag in (True, False):
        sub = [(x, y) for x, y, r in zip(a, b, rows) if r["match_exact"] is flag]
        sa, sb = [x for x, _ in sub], [y for _, y in sub]
        ns = len(sub)
        ks, pos, pes = kappa_from_sums(ns, sum(sa), sum(sb), sum(x and y for x, y in sub))
        tagn = "exact" if flag else "nonexact"
        rec(f"B2.{tagn}_n_children", ns, 708 if flag else None, tag="[C]", raw=raw)
        rec(f"B2.{tagn}_n_pairs", len({r['pair'] for r in rows if r['match_exact'] is flag}), tag="[C]", raw=raw)
        rec(f"B2.{tagn}_agreement", pos, "0.558" if flag else None, tag="[C]", raw=raw)
        rec(f"B2.{tagn}_chance", pes, "0.565" if flag else None, tag="[C]", raw=raw)
        rec(f"B2.{tagn}_kappa", ks, tag="[C]", raw=raw)
    rec("B3.ties_on_A_e", sum(r["margin_on_A"] == 0 for r in rows), 506, tag="[R]", raw=raw,
        cited="analysis/article_todos_2026-10-08.md:103")
    rec("B3.ties_on_B_e", sum(r["margin_on_B"] == 0 for r in rows), 560, tag="[R]", raw=raw,
        cited="analysis/article_todos_2026-10-08.md:103")
    # extra: HoVer siblings (own batch: SAME reflects on A_e, SWAP on B_e), for the draft :75 scope caveat
    cells = collections.defaultdict(list)
    for r in rows:
        cells[(r["pair"], r["arm"])].append((r["margin_on_A"] if r["arm"] == "SAME" else r["margin_on_B"]) > 0)
    ag = sum(sum(x == y for x, y in itertools.combinations(v, 2)) / 3 for v in cells.values()) / len(cells)
    p = sum(sum(v) for v in cells.values()) / sum(len(v) for v in cells.values())
    rec("B4.hover_sibling_agreement_own_batch", ag, tag="[C]", raw=raw,
        note=f"{len(cells)} cells; own batch: SAME->A_e, SWAP->B_e (hover_swap_analysis.py:6)")
    rec("B4.hover_sibling_chance_own_batch", p * p + (1 - p) ** 2, tag="[C]", raw=raw, note=f"p={p:.4f}")
    return dict(obs=po, chance=pe, n=n, kappa=k, sib_obs=ag, sib_chance=p * p + (1 - p) ** 2, sib_n=len(cells))


# ---------------------------------------------------------------- Part C: IFBench validation cost

def ifb_runs():
    """article_todos Appendix:442-447: the completed max_metric_calls==2500 baseline configs."""
    out = []
    for c in sorted(glob.glob("logs/baseline_seed*_b*.config.json")):
        cfg = json.load(open(c))
        if cfg.get("max_metric_calls") == 2500 and cfg.get("results", {}).get("completed"):
            out.append((c, cfg))
    assert len(out) == 10
    return out


def c_validation():
    runs = ifb_runs()
    per_run, info = [], []
    for cpath, cfg in runs:
        path, bsz = cfg["log_path"], cfg["b"]
        ev = [json.loads(l) for l in open(path) if l.strip()]
        val = {}
        for e in ev:
            if e["event"] == "valset_evaluated":
                assert e["candidate_idx"] not in val, (path, e["candidate_idx"])
                val[e["candidate_idx"]] = e
        acc = {e["new_candidate_idx"]: e for e in ev if e["event"] == "candidate_accepted"}
        end = [e for e in ev if e["event"] == "optimization_end"]
        assert len(end) == 1
        total, iters = end[0]["total_metric_calls"], end[0]["total_iterations"]
        split = collections.Counter()
        lt = eq = 0
        beat = {}                                          # accepted child idx -> exact valset mean > parent's
        for idx, e in val.items():
            ne = e["num_examples_evaluated"]
            if idx == 0:
                assert e["parent_ids"] == []
                split["seed"] += ne
                continue
            a = acc[idx]                                   # every non-seed valset eval is an accepted child
            assert len(a["parent_ids"]) == 1
            ce = exact_mean(list(e["scores_by_val_id"].values()))
            pe = exact_mean(list(val[a["parent_ids"][0]]["scores_by_val_id"].values()))
            lt += ce < pe; eq += ce == pe
            beat[idx] = ce > pe
            split["kept_better" if ce > pe else "kept_not_better"] += ne
        assert set(acc) == set(val) - {0}
        vsum = sum(e["num_examples_evaluated"] for e in val.values())
        assert vsum == sum(split.values())
        gate = sum(len(e["scores"]) for e in ev if e["event"] == "evaluation_end")
        gate_iters = len({e["iteration"] for e in ev if e["event"] == "evaluation_end"})
        rejected = [e for e in ev if e["event"] == "candidate_rejected"]
        sel = collections.Counter(e["candidate_idx"] for e in ev if e["event"] == "candidate_selected")
        parents = {a["parent_ids"][0] for a in acc.values()}
        best = end[0]["best_candidate_idx"]
        lin = collections.Counter()
        for idx, a in acc.items():
            g = "beat" if beat[idx] else "notbeat"
            later = sum(1 for e in ev if e["event"] == "candidate_selected" and e["candidate_idx"] == idx
                        and e["iteration"] > a["iteration"])
            assert later == sel[idx]                       # a candidate is never selected before it exists
            lin[f"{g}_n"] += 1; lin[f"{g}_selected"] += later > 0; lin[f"{g}_sel_events"] += later
            lin[f"{g}_had_accepted_child"] += idx in parents; lin[f"{g}_is_best"] += idx == best
        props = collections.defaultdict(list)
        for e in ev:
            if e["event"] == "proposal_end":
                props[e["iteration"]].append(e)
        logged = sum(any(isinstance(p.get("new_instructions"), dict) and p["new_instructions"]
                         and all(isinstance(v, str) and v.strip() for v in p["new_instructions"].values())
                         for p in props[r["iteration"]]) for r in rejected)
        row = dict(run=os.path.basename(path), b=bsz, total_metric_calls=total, total_iterations=iters,
                   valset_calls=vsum, val_seed=split["seed"], val_kept_better=split["kept_better"],
                   val_kept_not_better=split["kept_not_better"], other_calls=total - vsum,
                   gate_calls_from_evaluation_end=gate, iterations_with_gate_evals=gate_iters, accepted=len(acc), accepted_lt_parent=lt,
                   accepted_eq_parent=eq, rejected=len(rejected), rejected_with_logged_text=logged,
                   best_candidate_idx=best,
                   **{k: lin[k] for g in ("notbeat", "beat") for k in
                      (f"{g}_n", f"{g}_selected", f"{g}_sel_events", f"{g}_had_accepted_child", f"{g}_is_best")})
        st = [e for e in ev if e["event"] == "optimization_start"]
        assert len(st) == 1
        ex = {idx: exact_mean(list(e["scores_by_val_id"].values())) for idx, e in val.items()}
        row["seed_valset_mean"] = repr(float(ex[0]))
        per_run.append(row)
        info.append(dict(run=os.path.basename(path), b=bsz, ex=ex, acc=acc, beat=beat, best=best, ev=ev,
                         val0=val[0]["scores_by_val_id"],
                         seed_hash=hashlib.sha256(json.dumps(st[0]["seed_candidate"], sort_keys=True).encode()).hexdigest(),
                         val_ids=tuple(sorted(val[0]["scores_by_val_id"], key=str))))
    write_csv("c_budget_by_run.csv", per_run)
    src = "logs/baseline_seed*_b*.jsonl (10 runs, article_todos:442-447)"
    for grp, sel in (("all", lambda r: True), ("b3", lambda r: r["b"] == 3), ("b1", lambda r: r["b"] == 1)):
        rs = [r for r in per_run if sel(r)]
        S = {k: sum(r[k] for r in rs) for k in per_run[0] if k not in ("run", "b", "best_candidate_idx", "seed_valset_mean")}
        refs = {"all": (145, 73, "0.5034"), "b3": (115, 53, "0.4609"), "b1": (30, 20, "0.6667")}[grp]
        cl = {"all": "148", "b3": "149", "b1": "150"}[grp]
        cited = f"analysis/article_todos_2026-10-08.md:{cl}"
        rec(f"C1.{grp}_runs", len(rs), tag="[R]", raw=src, cited=cited)
        rec(f"C1.{grp}_accepted", S["accepted"], refs[0], tag="[R]", raw=src, cited=cited)
        rec(f"C1.{grp}_did_not_beat_parent", S["accepted_lt_parent"] + S["accepted_eq_parent"], refs[1],
            tag="[R]", raw=src, cited=cited)
        rec(f"C1.{grp}_ties", S["accepted_eq_parent"], 0, tag="[R]", raw=src, cited=cited)
        rec(f"C1.{grp}_rate", (S["accepted_lt_parent"] + S["accepted_eq_parent"]) / S["accepted"], refs[2],
            tag="[R]", raw=src, cited=cited)
        rec(f"C2.{grp}_valset_calls", S["valset_calls"], 23250 if grp == "all" else None, tag="[C]", raw=src)
        rec(f"C2.{grp}_total_metric_calls", S["total_metric_calls"], 25829 if grp == "all" else None, tag="[C]", raw=src)
        rec(f"C2.{grp}_valset_share", S["valset_calls"] / S["total_metric_calls"], "0.90" if grp == "all" else None,
            tag="[C]", raw=src)
        rec(f"C3.{grp}_val_seed_prompt", S["val_seed"], tag="[C]", raw=src)
        rec(f"C3.{grp}_val_kept_beat_parent", S["val_kept_better"], tag="[C]", raw=src)
        rec(f"C3.{grp}_val_kept_did_not_beat", S["val_kept_not_better"], tag="[C]", raw=src)
        rec(f"C3.{grp}_everything_else", S["other_calls"], tag="[C]", raw=src,
            note="total_metric_calls - valset calls")
        rec(f"C3.{grp}_everything_else_equals_evaluation_end_sum",
            "yes" if S["other_calls"] == S["gate_calls_from_evaluation_end"] else
            f"no ({S['gate_calls_from_evaluation_end']})", tag="[C]", raw=src)
        rec(f"C4.{grp}_rejected_children", S["rejected"], 267 if grp == "b3" else None, tag="[C]", raw=src)
        rec(f"C4.{grp}_rejected_with_text_in_proposal_end", S["rejected_with_logged_text"],
            S["rejected"], tag="[C]", raw=src, note="same-iteration proposal_end.new_instructions, non-empty")
        if grp in ("all", "b3"):
            rec(f"C6.{grp}_kept_validation_share_of_all_calls",
                (S["val_kept_better"] + S["val_kept_not_better"]) / S["total_metric_calls"], tag="[C]", raw=src,
                note=f"({S['val_kept_better']}+{S['val_kept_not_better']})/{S['total_metric_calls']}")
            rec(f"C6.{grp}_kept_not_beat_validation_share_of_all_calls",
                S["val_kept_not_better"] / S["total_metric_calls"], tag="[C]", raw=src,
                note=f"{S['val_kept_not_better']}/{S['total_metric_calls']}")
        if grp == "b3":
            assert S["notbeat_n"] + S["beat_n"] == S["accepted"] == 115
            for g, lab, ref in (("notbeat", "did_not_beat_parent", 53), ("beat", "beat_parent_COMPARISON", None)):
                rec(f"C7.b3_{lab}_n", S[f"{g}_n"], ref, tag="[C]", raw=src)
                rec(f"C7.b3_{lab}_later_selected_as_parent", S[f"{g}_selected"], tag="[C]", raw=src,
                    note=f"children with >=1 candidate_selected after acceptance; {S[f'{g}_sel_events']} selection events")
                rec(f"C7.b3_{lab}_had_accepted_child", S[f"{g}_had_accepted_child"], tag="[C]", raw=src,
                    note="appears as parent_ids[0] of some candidate_accepted")
                rec(f"C7.b3_{lab}_is_returned_best", S[f"{g}_is_best"], tag="[C]", raw=src,
                    note="== optimization_end.best_candidate_idx")
        if grp != "all":
            bsz = 3 if grp == "b3" else 1
            rec(f"C5.{grp}_gate_calls_per_iteration", S["other_calls"] / S["total_iterations"], tag="[C]", raw=src,
                note=f"compare 2b = {2 * bsz}; iterations whose proposal is skipped/fails pay only b")
            rec(f"C5.{grp}_iterations", S["total_iterations"], tag="[C]", raw=src, note="optimization_end.total_iterations")
            rec(f"C5.{grp}_iterations_with_gate_evals", S["iterations_with_gate_evals"], tag="[C]", raw=src,
                note="distinct iterations logging evaluation_end; 1 more per run than total_iterations (the final, budget-exhausting iteration)")
            rec(f"C5.{grp}_gate_calls_per_evaluated_iteration", S["other_calls"] / S["iterations_with_gate_evals"], tag="[C]",
                raw=src, note="iterations with no child evaluation (proposal skipped/failed) pay b, not 2b")
            rec(f"C5.{grp}_all_metric_calls_per_iteration", S["total_metric_calls"] / S["total_iterations"], tag="[C]",
                raw=src, note="includes full-valset evaluation of every kept rewrite; excludes the proposer LM call")
    c_lineage_noise(info, src)
    fig = []
    for grp, sel in (("all 10 runs", lambda r: True), ("b=3 (8 runs)", lambda r: r["b"] == 3),
                     ("b=1 (2 runs)", lambda r: r["b"] == 1)):
        rs = [r for r in per_run if sel(r)]
        for cat, key in (("validation: seed prompt", "val_seed"), ("validation: kept, beat parent", "val_kept_better"),
                         ("validation: kept, did not beat parent", "val_kept_not_better"),
                         ("everything else (minibatch gate)", "other_calls")):
            fig.append(dict(group=grp, category=cat, calls=sum(r[key] for r in rs)))
    write_csv("fig_budget.csv", fig)
    return info


def c_lineage_noise(info, src):
    """C8 argmax check, C9 lineage of each returned best, N1 seed-prompt valset noise, N2 kept-rewrite improvement."""
    import numpy as np
    b3 = [r for r in info if r["b"] == 3]
    assert len(b3) == 8
    # C8: best_candidate_idx is the unique argmax of the exact valset means
    for grp, rs in (("all", info), ("b3", b3)):
        ok = 0
        for r in rs:
            mx = max(r["ex"].values())
            ok += [k for k, v in r["ex"].items() if v == mx] == [r["best"]]
        rec(f"C8.{grp}_best_is_unique_exact_argmax", ok, len(rs), tag="[C]", raw=src,
            note="optimization_end.best_candidate_idx vs argmax of exact valset means; so a child <= its parent can never be returned")
    # C9: lineage of the returned best
    rows, hit = [], {}
    for r in info:
        idx, depth, chain = r["best"], 0, []
        while True:
            par = r["acc"][idx]["parent_ids"][0] if idx != 0 else ""
            rows.append(dict(run=r["run"], b=r["b"], depth=depth, cand_idx=idx, parent_idx=par,
                             valset_mean=repr(float(r["ex"][idx])), is_seed=idx == 0,
                             beat_parent="" if idx == 0 else r["beat"][idx]))
            chain.append(idx)
            if idx == 0:
                break
            idx, depth = par, depth + 1
        hit[r["run"]] = (any(not r["beat"][i] for i in chain if i != 0), len(chain) - 1, r["b"])
    write_csv("c_lineage.csv", rows)
    for grp, sel in (("all", lambda b: True), ("b3", lambda b: b == 3)):
        runs = [k for k, (h, _, b) in hit.items() if h and sel(b)]
        rec(f"C9.{grp}_returned_best_chain_contains_not_beat_child", len(runs), 4 if grp == "b3" else None, tag="[C]",
            raw=src, note="runs: " + ", ".join(k.split("_2026")[0] for k in runs))
    rec("C9.b3_runs_with_hit", ",".join(sorted(k.split("_")[1] for k, (h, _, b) in hit.items() if h and b == 3)),
        "seed1,seed3,seed6,seed7", tag="[C]", raw=src)
    rec("C9.chain_lengths_accepted_steps", "; ".join(f"{k.split('_2026')[0]}={n}" for k, (_, n, _) in hit.items()),
        tag="[C]", raw=src, note="accepted children between the seed and the returned best (c_lineage.csv)")
    # N1: seed prompt, same 150 items, evaluated once per run
    rec("N1.distinct_seed_prompts", len({r["seed_hash"] for r in info}), 1, tag="[C]", raw=src,
        note="sha256 of optimization_start.seed_candidate")
    rec("N1.distinct_valset_id_sets", len({r["val_ids"] for r in info}), 1, tag="[C]", raw=src,
        note=f"{len(info[0]['val_ids'])} ids")
    seeds = [r["ex"][0] for r in info]
    for r in info:
        rec(f"N1.seed_valset_mean_{r['run'].split('_2026')[0]}", float(r["ex"][0]), tag="[C]", raw=src)
    mu = sum(seeds) / len(seeds)
    sd = math.sqrt(float(sum((x - mu) ** 2 for x in seeds) / (len(seeds) - 1)))
    rec("N1.seed_valset_mean_mean", float(mu), tag="[C]", raw=src)
    rec("N1.seed_valset_mean_sd_ddof1", sd, "0.015", tag="[C]", raw=src,
        note="same prompt, same 150 items, 10 evaluations: task-LM resampling noise of one valset mean")
    rec("N1.seed_valset_mean_min", float(min(seeds)), "0.505", tag="[C]", raw=src)
    rec("N1.seed_valset_mean_max", float(max(seeds)), "0.560", tag="[C]", raw=src)
    # N2: child - parent valset mean, b=3 accepted children
    per = [[r["ex"][i] - r["ex"][r["acc"][i]["parent_ids"][0]] for i in sorted(r["acc"])] for r in b3]
    d = sorted(x for p in per for x in p)
    assert len(d) == 115
    rec("N2.b3_n_accepted", len(d), 115, tag="[C]", raw=src)
    rec("N2.b3_mean_child_minus_parent", float(sum(d) / len(d)), "+0.001", tag="[C]", raw=src, note="exact rationals")
    rec("N2.b3_median_child_minus_parent", float(d[len(d) // 2]), tag="[C]", raw=src, note="exact; n odd")
    rng = np.random.default_rng(SEED0 + 20)
    arr = [np.array([float(x) for x in p]) for p in per]
    bm = [np.concatenate([arr[j] for j in rng.integers(0, 8, 8)]).mean() for _ in range(NBOOT)]
    lo, hi = float(np.percentile(bm, 2.5)), float(np.percentile(bm, 97.5))
    rec("N2.b3_mean_ci95_lo_run_cluster", lo, "-0.002", tol=MC_TOL, tag="[C]", raw=src,
        note=f"percentile, {NBOOT} resamples of 8 runs, rng {SEED0 + 20}")
    rec("N2.b3_mean_ci95_hi_run_cluster", hi, "+0.005", tol=MC_TOL, tag="[C]", raw=src,
        note=f"percentile, {NBOOT} resamples of 8 runs, rng {SEED0 + 20}")
    thr = math.sqrt(2) * sd
    rec("N2.b3_share_abs_diff_below_sqrt2_sd", sum(abs(float(x)) < thr for x in d) / len(d), "0.70", tag="[C]", raw=src,
        note=f"threshold sqrt(2) x N1 sd = {thr:.5f}: the sd of a difference of two independent evaluations of one prompt")


# ---------------------------------------------------------------- Part D: HoVer three-arm

def sd_runs():
    out = {}
    for arm in "BCT":
        for s in range(8):
            d = f"{SD_RUNS}/{arm}_seed{s}"
            out[(arm, s)] = (json.load(open(f"{d}/endpoints.json")), d)
    return out


def _mean_sd(xs):
    n = len(xs); mu = sum(xs) / n
    return mu, math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))


def d_three_arm():
    runs = sd_runs()
    # D1
    hs = {}
    for (arm, s), (_, d) in runs.items():
        g = json.load(open(f"{d}/gepa_result.json"))
        hs[f"{arm}_seed{s}"] = hashlib.sha256(json.dumps(g["program_candidates"][0], sort_keys=True).encode()).hexdigest()
    rec("D1.distinct_seed_program_hashes", len(set(hs.values())), 1, tag="[C]",
        raw=f"{SD_RUNS}/*_seed*/gepa_result.json program_candidates[0]", note=f"sha256 {sorted(set(hs.values()))[0][:16]}...")
    # D2
    rows = []
    for (arm, s), (e, d) in sorted(runs.items()):
        if e["sel_returned_seed_prompt"]:
            tie = bool(e["sel_tie_broken"]) and 0 in e["sel_tied_indices"]
            rows.append(dict(run=e["run"], sel_best_idx=e["sel_best_idx"], sel_tied_indices=json.dumps(e["sel_tied_indices"]),
                             tie_broken_toward_0=tie, seed_selection_mean=e["selection_means"][0],
                             endpoint_test_mean=e["endpoint_test_mean"]))
    write_csv("d2_seed_prompt_runs.csv", rows)
    raw = f"{SD_RUNS}/*_seed*/endpoints.json"
    rec("D2.runs_returning_seed_prompt", ",".join(r["run"] for r in rows), "B_seed2,C_seed1,C_seed7,T_seed2,T_seed5",
        tag="[C]", raw=raw)
    rec("D2.n_seed_prompt_runs", len(rows), 5, tag="[C]", raw=raw)
    rec("D2.n_tie_broken_toward_index0", sum(r["tie_broken_toward_0"] for r in rows), 2, tag="[C]", raw=raw,
        cited="analysis/state_dep/score_candidates.py:9 (ties -> LOWEST index)",
        note="runs: " + ",".join(r["run"] for r in rows if r["tie_broken_toward_0"]))
    mu, sd = _mean_sd([r["endpoint_test_mean"] for r in rows])
    rec("D2.seed_prompt_test_mean", mu, "0.5751", tag="[C]", raw=raw)
    rec("D2.seed_prompt_test_sd_ddof1", sd, "0.0110", tag="[C]", raw=raw)
    # D3
    bmu, bsd = _mean_sd([runs[("B", s)][0]["endpoint_test_mean"] for s in range(8)])
    rec("D3.armB_test_mean", bmu, "0.599167", tag="[R]", raw=raw, cited="analysis/state_dep/results.md:130")
    rec("D3.armB_minus_seed_prompt", bmu - mu, tag="[C]", raw=raw,
        note="n=8 vs n=5; the 5 are selected (seed won selection); same 150-claim test split; spread among the 5 is task-LM resampling of one prompt")
    # D4
    s0 = [runs[k][0]["selection_means"][0] for k in sorted(runs)]
    mu0, sd0 = _mean_sd(s0)
    rec("D4.seed_selection_score_min", min(s0), "0.5067", tag="[C]", raw=raw)
    rec("D4.seed_selection_score_max", max(s0), "0.6133", tag="[C]", raw=raw)
    rec("D4.seed_selection_score_sd_ddof1", sd0, "0.0267", tag="[C]", raw=raw)
    rec("D4.seed_selection_score_mean", mu0, tag="[C]", raw=raw)
    sc = open("analysis/state_dep/score_candidates.py").read().splitlines()
    es = open("analysis/state_dep/eval_split.py").read().splitlines()
    ok = ("EVERY candidate including index 0" in sc[7] and "for i, c in enumerate(cands):" in sc[107]
          and "ev.open_task_lm(dspy)" in sc[99] and "cache=False" in es[233])
    rec("D4.index0_scored_fresh_cache_off", "confirmed" if ok else "NOT CONFIRMED", "confirmed", tag="[C]",
        raw="analysis/state_dep/score_candidates.py:8,100,108-110; analysis/state_dep/eval_split.py:233-234")
    # D5
    beta = 0.0379395028680125
    rec("D5.planned_one_step_effect_1.4432xbeta/2", 1.4431827353722393 * beta / 2, "0.02738", tag="[R]",
        cited="analysis/state_dep/plan.md:357 (D at :347)", note="one-step specificity units, not endpoint")
    rec("D5.realized_dose_1.2185xbeta/2", 1.2185 * beta / 2, tag="[C]",
        cited="D from analysis/manipulation_check_2026-09-28.md:178", note="one-step specificity units, not endpoint")
    UN = "batch total, 0-3 scale (hover_swap_analysis.py:131, screen_part05_outcomes.py:70 divide integer-thirds batch margins by 3)"
    planned, realized, mde = 1.4431827353722393 * beta / 2, 1.2185 * beta / 2, 0.06331761163202784
    rec("D5.planned_per_example", planned / 3, tag="[C]", note="planned effect / 3; per-example, 0-1 scale (same scale as the endpoint)")
    rec("D5.realized_per_example", realized / 3, tag="[C]", note="realized-dose effect / 3; per-example, 0-1 scale")
    rec("D5.units_of_effect_and_beta", UN, tag="[C]")
    rec("D5.MDE_over_planned_cross_scale", mde / planned, "2.3", tag="[R]", cited="analysis/state_dep/plan.md:357",
        note="per-claim-mean MDE (0-1) / batch-total effect (0-3): crosses scales")
    rec("D5.MDE_over_planned_per_example", mde / (planned / 3), tag="[C]", note="both on the per-example 0-1 scale")
    rec("D5.MDE_over_realized_per_example", mde / (realized / 3), tag="[C]", note="both on the per-example 0-1 scale")
    rec("D5.realized_gate_trigger_3x(1.2185xbeta/2)", 3 * 1.2185 * beta / 2, "0.06934", tag="[R]",
        cited="analysis/manipulation_check_2026-09-28.md:288; GATE_K=3 at analysis/state_dep/mde_sim.py:35",
        note="the x3 is the gate trigger multiplier, not an effect size")
    # D6
    end = {(a, s): runs[(a, s)][0]["endpoint_test_mean"] for a in "BCT" for s in range(8)}
    for lab, x, y in (("T-C", "T", "C"), ("T-B", "T", "B"), ("C-B", "C", "B")):
        d8 = [end[(x, s)] - end[(y, s)] for s in range(8)]
        o8, p8 = signflip_exact(d8)
        d7 = [d8[s] for s in range(8) if s != 4]
        o7, p7 = signflip_exact(d7)
        r8 = {"T-C": ("-0.001111", "0.968750")}.get(lab, (None, None))
        r7 = {"T-C": ("-0.015556", "0.078125"), "T-B": ("-0.027302", "0.046875"), "C-B": ("-0.011746", "0.156250")}[lab]
        cw = "analysis/WEBSITE-2026-09-28.md:69" if lab == "T-C" else None
        rec(f"D6.{lab}_n8_mean", o8, r8[0], tag="[R]" if cw else "[C]", raw=raw, cited=cw or "")
        rec(f"D6.{lab}_n8_signflip_p", p8, r8[1], tag="[R]" if cw else "[C]", raw=raw, cited=cw or "")
        rec(f"D6.{lab}_seed4_diff", d8[4], "+0.100000" if lab == "T-C" else None, tag="[R]" if lab == "T-C" else "[C]",
            raw=raw, cited="analysis/WEBSITE-2026-09-28.md:121" if lab == "T-C" else "")
        rec(f"D6.{lab}_drop_seed4_mean", o7, r7[0], tag="[R]", raw=raw, cited="analysis/WEBSITE-2026-09-28.md:135")
        rec(f"D6.{lab}_drop_seed4_signflip_p_n7", p7, r7[1], tag="[R]", raw=raw,
            cited="analysis/WEBSITE-2026-09-28.md:140-141", note="post hoc")
    # D7
    hs_m = load_module("hs2", "analysis/ablation/hover_swap/hover_swap_analysis.py")
    found = collections.Counter(); detail = []
    for lab, paths in (("stage1", [f"scratch/hover_stage1/stage1_seed{s}/gepa_result.json" for s in range(8)]),
                       ("three_arm", [f"{SD_RUNS}/{a}_seed{s}/gepa_result.json" for a in "BCT" for s in range(8)])):
        for p in paths:
            g = json.load(open(p))
            for t in g["full_program_trace"]:
                if "new_subsample_scores" not in t or "new_program_idx" not in t:
                    continue
                fl = sum(t["new_subsample_scores"]) > sum(t["subsample_scores"])
                ex = sum(hs_m.thirds(t["new_subsample_scores"])) > sum(hs_m.thirds(t["subsample_scores"]))
                assert fl, (p, t["i"])                  # every accepted trace entry passes the float gate
                if not ex:
                    found[lab] += 1
                    detail.append(f"{p.split('/')[-2]} i={t['i']} new_program_idx={t['new_program_idx']}")
    rec("D7.stage1_float_tie_accepts", found["stage1"], 2, tag="[R]", raw="scratch/hover_stage1/stage1_seed{0..7}/gepa_result.json",
        cited="analysis/article_todos_2026-10-08.md:264-269")
    rec("D7.three_arm_float_tie_accepts", found["three_arm"], 3, tag="[C]", raw=f"{SD_RUNS}/*_seed*/gepa_result.json",
        note="; ".join(d for d in detail if "stage1" not in d))
    rec("D7.total_float_tie_accepts", found["stage1"] + found["three_arm"], 5, tag="[C]", raw="both")


# ---------------------------------------------------------------- Part E: screen calibration

def excl0(r): return not math.isnan(r["lo"]) and (r["lo"] > 0 or r["hi"] < 0)
def crit_a(rec_, c): r = rec_[c]["41"]; return excl0(r) and r["loro"] >= 7 and r["p"] < 0.05
def crit_b(rec_, c): r = rec_[c]["42"]; return crit_a(rec_, c) and excl0(r) and r["p"] < 0.05
def survivors(o): return [c for c in o["cells"] if crit_b(o["cells"], c) and c in o["mcb"]]


def e_screen():
    d = json.load(open(PERM))
    assert sorted(d, key=int) == [str(i) for i in range(201)]
    s0 = survivors(d["0"])
    obs = d["0"]["cells"]["knn_emb_fb_min"]["41"]["beta"]
    rec("E0.identity_survivors", ",".join(s0), "knn_emb_fb_min", tag="[R]", raw=PERM,
        cited="analysis/review_response_2026-08-26/03_permutation_calibration.md:30,62")
    rec("E0.observed_beta", obs, "0.0379395", tag="[R]", raw=PERM, cited="analysis/hover_screen/results.md:91")
    c = collections.Counter()
    srows = []
    for k in map(str, range(1, 201)):
        b = [d[k]["cells"][x]["41"]["beta"] for x in survivors(d[k])]
        c["any"] += bool(b); c["abs"] += any(abs(x) >= obs for x in b); c["pos"] += any(x >= obs for x in b)
        top = max(b, key=abs) if b else None
        srows.append(dict(perm=int(k), n_survivors=len(b), max_abs_beta="" if top is None else repr(abs(top)),
                          sign_of_max="" if top is None else ("+" if top > 0 else "-")))
    write_csv("fig_screen_null_survivors.csv", srows)
    rec("E3.perms_with_no_survivor", sum(r["n_survivors"] == 0 for r in srows), 200 - 134, tag="[C]", raw=PERM)
    rec("E3.perms_survivor_max_abs_beta_ge_obs", sum(r["max_abs_beta"] != "" and float(r["max_abs_beta"]) >= obs
                                                    for r in srows), 43, tag="[C]", raw=PERM,
        note="per shuffle, largest |beta| among full-rule survivors (E1 rule)")
    rec("E1.perms_with_any_survivor", c["any"], 134, tag="[R]", raw=PERM,
        cited="analysis/review_response_2026-08-26/03_permutation_calibration.md:44")
    rec("E1.perms_with_survivor_abs_beta_ge_obs", c["abs"], 43, tag="[R]", raw=PERM,
        cited="analysis/article_todos_2026-10-08.md:36 ([C] there)")
    rec("E1.perms_with_survivor_beta_ge_obs_same_sign", c["pos"], 20, tag="[R]", raw=PERM,
        cited="analysis/WEBSITE-2026-09-28.md:176 ([C] there); article_todos:35")
    obs_max = max(v["41"]["beta"] for v in d["0"]["cells"].values())
    rows, mx = [], []
    for k in map(str, range(1, 201)):
        cells = d[k]["cells"]
        assert len(cells) == 108
        m = max(v["41"]["beta"] for v in cells.values())
        assert abs(m - d[k]["max_beta"]) < 1e-12, (k, m, d[k]["max_beta"])
        mx.append(m); rows.append(dict(perm=int(k), null_max_beta=repr(m)))
    write_csv("fig_screen_null.csv", rows)
    rec("E2.cells_per_permutation", 108, 108, tag="[R]", raw=PERM)
    rec("E2.stored_max_beta_crosscheck", "200/200 equal", "200/200 equal", tag="[C]", raw=PERM)
    rec("E2.null_max_ge_observed_beta", sum(x >= obs for x in mx), 93, tag="[R]", raw=PERM,
        cited="analysis/review_response_2026-08-26/03_permutation_calibration.md:68")
    rec("E2.observed_percentile_strict", sum(x < obs for x in mx) / 200, tag="[C]", raw=PERM,
        note="share of the 200 null maxima strictly below observed beta")
    rec("E2.observed_percentile_le", sum(x <= obs for x in mx) / 200, tag="[C]", raw=PERM)
    rec("E2.observed_max_beta_all108", obs_max, tag="[R]", raw=PERM,
        cited="analysis/review_response_2026-08-26/03_permutation_calibration.md:62-63")
    rec("E2.null_max_ge_observed_max", sum(x >= obs_max for x in mx), 17, tag="[R]", raw=PERM,
        cited="analysis/review_response_2026-08-26/03_permutation_calibration.md:67")
    # draft :58 screen size and p
    rec("X.screen_cells", len(d["0"]["cells"]), 108, tag="[R]", raw=PERM, cited="analysis/WEBSITE-2026-09-28.md:178")
    r41 = d["0"]["cells"]["knn_emb_fb_min"]["41"]
    rec("X.screen_survivor_p", r41["p"], "0.0013", tag="[R]", raw=PERM, cited="analysis/hover_screen/results.md:91")
    rec("X.screen_survivor_ci_lo", r41["lo"], "0.010447", tag="[R]", raw=PERM, cited="analysis/WEBSITE-2026-09-28.md:188")
    rec("X.screen_survivor_ci_hi", r41["hi"], "0.070305", tag="[R]", raw=PERM, cited="analysis/WEBSITE-2026-09-28.md:188")


# ---------------------------------------------------------------- extra draft numbers

def x_ablation():
    rows = list(csv.DictReader(open("analysis/ablation/calls.csv")))
    by = collections.defaultdict(dict)
    col = collections.Counter()
    for r in rows:
        if r["arm"] in ("i", "ii", "iii"):
            acc = float(r["child_score_sum"]) > float(r["parent_score_sum_today"])   # run_ablation_analysis.py:28
            by[r["batch_id"]][r["arm"]] = acc
            col[r["arm"]] += r["accept_today"] == "1"
    raw = "analysis/ablation/calls.csv"
    dis = [(i + 2, r["batch_id"], r["arm"], r["child_score_sum"], r["parent_score_sum_today"], r["accept_today"])
           for i, r in enumerate(rows)
           if (r["accept_today"] == "1") != (float(r["child_score_sum"]) > float(r["parent_score_sum_today"]))]
    rec("X.ablation_accept_today_disagreements", "; ".join(f"{b}/{a} {c} vs {p} accept_today={t} (csv:{ln})"
                                                           for ln, b, a, c, p, t in dis),
        "s6_it4/i 1.5 vs 1.5 accept_today=1 (csv:380); s6_it4/i_rep 1.5 vs 1.5 accept_today=1 (csv:382); "
        "s6_it4/iii 1.5 vs 1.5 accept_today=1 (csv:383)", tag="[C]", raw=raw,
        cited="scripts/run_ablation.py:153-155 (accept_today = int(c_sum > p_sum) on unrounded sums; sums written rounded to 4 dp)",
        note="the only rows where accept_today disagrees with the rounded comparison: one batch, three calls, float ties")
    rec("X.ablation_float_tie_batches", len({b for _, b, *_ in dis}), 1, tag="[C]", raw=raw)
    rec("X.ablation_float_tie_calls", len(dis), 3, tag="[C]", raw=raw)
    for arm, ref, ln in (("i", "0.340", 30), ("ii", "0.313", 31), ("iii", "0.367", 32)):
        v = [b[arm] for b in by.values()]
        rec(f"X.ablation_keep_rate_{arm}", sum(v) / len(v), ref, tag="[R]", raw=raw,
            cited=f"analysis/ablation/results.md:{ln}; findings_summary.md:51",
            note=f"{sum(v)}/{len(v)}; accept = child_score_sum > parent_score_sum_today (scripts/run_ablation_analysis.py:28); "
                 f"the accept_today column gives {col[arm]}")
        ties = sum(1 for _, b, a, *_ in dis if a == arm)
        rec(f"X.ablation_accept_today_minus_float_ties_{arm}", col[arm] - ties, sum(v), tag="[C]", raw=raw,
            note=f"{col[arm]} - {ties} float tie(s) reconciles the column with the committed count")
    for a1, a2, ref, ln in (("i", "iii", "0.63", 36), ("i", "ii", "0.65", 37)):
        bc = sum(by[k][a1] and not by[k][a2] for k in by)
        cb = sum(by[k][a2] and not by[k][a1] for k in by)
        n = bc + cb
        p = min(1.0, 2 * sum(math.comb(n, j) for j in range(min(bc, cb) + 1)) / 2 ** n)
        rec(f"X.ablation_mcnemar_exact_p_{a1}_vs_{a2}", p, ref, tag="[R]", raw=raw,
            cited=f"analysis/ablation/results.md:{ln}", note=f"discordant {bc}/{cb}, exact binomial two-sided")


def x_hover_swap(m):
    import numpy as np
    by = collections.defaultdict(list)
    for r in m.load():
        by[r["pair"]].append(r)
    S, Tr, C = [], [], []
    for pid, rs in sorted(by.items()):
        aS, aW = m.draw_avg(rs, "SAME", "margin_on_A"), m.draw_avg(rs, "SWAP", "margin_on_A")
        bS, bW = m.draw_avg(rs, "SAME", "margin_on_B"), m.draw_avg(rs, "SWAP", "margin_on_B")
        S.append((((aS - aW) + (bW - bS)) / 2) / 3.0); Tr.append(((bS + aW) / 2) / 3.0); C.append(rs[0]["seed"])
    S, Tr, C = np.array(S), np.array(Tr), np.array(C)
    m.rng = np.random.default_rng(20260703)                   # replay hover_swap_analysis.main()'s chain
    so, sp = m.perm_p(S)
    lo, hi, se = m.cluster_boot(S, C)
    [np.mean(m.rng.choice(S, len(S))) for _ in range(m.NBOOT)]
    to, tp = m.perm_p(Tr)
    raw = f"{HOVER_PAIRS}/*/draws.jsonl via hover_swap_analysis.py"
    cited = "analysis/ablation/hover_swap/results.md:11"
    rec("X.hover_spec_point", so, "+0.0274", tag="[R]", raw=raw, cited=cited)
    rec("X.hover_spec_perm_p", sp, "0.0177", tag="[R]", raw=raw, cited=cited)
    rec("X.hover_spec_ci_lo", lo, "+0.0149", tag="[R]", raw=raw, cited=cited)
    rec("X.hover_spec_ci_hi", hi, "+0.0415", tag="[R]", raw=raw, cited=cited)
    for nm, v in (("point", so), ("ci_lo", lo), ("ci_hi", hi)):
        rec(f"X.hover_spec_{nm}_per_example", v / 3, tag="[C]", raw=raw,
            note="batch-total specificity (0-3 scale, hover_swap_analysis.py:131) / 3 = per-example (0-1)")
    rec("X.hover_transfer_point", to, "+0.0169", tag="[R]", raw=raw, cited="analysis/ablation/hover_swap/results.md:12")
    rec("X.hover_transfer_perm_p", tp, "0.3120", tag="[R]", raw=raw, cited="analysis/ablation/hover_swap/results.md:12")


def x_mde():
    import numpy as np
    ms = load_module("mde_sim", "analysis/state_dep/mde_sim.py")
    pts = np.asarray(json.load(open("analysis/state_dep/stage1_backfill_endpoints.json"))["endpoints"], dtype=float)
    mde, _ = ms.find_mde(pts, np.random.default_rng(20260709))        # mde_sim.report():81,88
    rec("X.three_arm_MDE", mde, "0.06332", tag="[R]", raw="analysis/state_dep/stage1_backfill_endpoints.json via mde_sim.find_mde",
        cited="analysis/state_dep/plan.md:345; results.md:10", note="endpoint units; assumes rho=0")
    src = open("scripts/batch_swap_v2_analysis.py").read().splitlines()
    rec("X.ifb_swap_MDE_constant", "0.033" if "3: 0.033" in src[21] else "?", "0.033", tag="cited",
        cited="scripts/batch_swap_v2_analysis.py:22; batch_swap_v2/results.md:8,11",
        note="Stage-0 constant MDE_SPEC[3], not recomputed from data here")
    rec("X.ablation_MDE_pp", "10-12", "10-12", tag="cited", cited="analysis/ablation/plan.md:39; results.md:17",
        note="Stage-0 analytic estimate, not recomputed here")


def x_models():
    runs = ifb_runs()
    import linecache
    t = {linecache.getline(c, 8).strip() for c, _ in runs}
    r = {linecache.getline(c, 9).strip() for c, _ in runs}
    rec("X.ifb_task_lm_lines8", " | ".join(sorted(t)), tag="[R]", raw="logs/baseline_*.config.json:8",
        cited="analysis/article_todos_2026-10-08.md:228-237")
    rec("X.ifb_reflection_lm_lines9", " | ".join(sorted(r)), tag="[R]", raw="logs/baseline_*.config.json:9",
        cited="analysis/article_todos_2026-10-08.md:228-237")
    tl, rl = set(), set()
    for (arm, s), (_, d) in sd_runs().items():
        cfg = json.load(open(f"{d}/config.json"))
        tl.add(cfg["task_lm"]["model"]); rl.add(cfg["reflection_lm"]["model"])
    rec("X.hover_task_lm", ",".join(sorted(tl)), "openai/gpt-4.1-mini", tag="[R]", raw=f"{SD_RUNS}/*/config.json")
    rec("X.hover_reflection_lm", ",".join(sorted(rl)), "openai/gpt-4.1-mini", tag="[R]", raw=f"{SD_RUNS}/*/config.json",
        cited="analysis/WEBSITE-2026-09-28.md:285")


def x_cost():
    base = "analysis/state_dep"
    led = json.load(open(f"{base}/liverun_ledger.json"))
    live = sum(r["spend_usd"] for r in led)
    rec("X.cost_liverun_ledger_48rows", live, "132.7603", tag="[R]", raw=f"{base}/liverun_ledger.json",
        cited="analysis/WEBSITE-2026-09-28.md:307", note=f"{len(led)} rows")
    def dollars(path, line, pat=r"\$([\d.]+)"):
        return float(re.search(pat, open(path, newline="").read().split("\n")[line - 1]).group(1))
    tsplit = json.load(open(f"{base}/test_pool_summary.json"))["spend_usd"]
    rec("X.cost_test_split", tsplit, "3.2336", tag="[R]", raw=f"{base}/test_pool_summary.json:7",
        cited="analysis/WEBSITE-2026-09-28.md:305")
    smoke = dollars(f"{base}/markers/SMOKE.DONE", 25, r"([\d.]+)")
    dose = sum(dollars(f"{base}/logs/dose_compute.out", n) for n in (145, 574, 739))
    back = dollars(f"{base}/logs/backfill.log", 129) + dollars(f"{base}/logs/backfill.log", 13) + dollars(f"{base}/logs/backfill.out", 7)
    rec("X.cost_smoke", smoke, "5.1942", tag="[R]", raw=f"{base}/markers/SMOKE.DONE:25", cited="analysis/WEBSITE-2026-09-28.md:306")
    rec("X.cost_dose", dose, "8.3355", tag="[R]", raw=f"{base}/logs/dose_compute.out:145,574,739", cited="analysis/WEBSITE-2026-09-28.md:308")
    rec("X.cost_backfill", back, "39.3907", tag="[R]", raw=f"{base}/logs/backfill.log:13,129; backfill.out:7",
        cited="analysis/WEBSITE-2026-09-28.md:309", note="$1.384 term is a last-printed meter (lower bound)")
    rec("X.cost_total_lower_bound", round(tsplit + live + smoke + dose + back, 4), "188.9143", tag="[R]", raw="sum of the five",
        cited="analysis/WEBSITE-2026-09-28.md:311-313", note="lower bound: dose-control pass not recorded (WEBSITE:310)")


# ---------------------------------------------------------------- Part F: HotpotQA

def f_hotpot():
    import numpy as np
    head = git("rev-parse", "HEAD").strip()
    rec("F.frontier_gepa_HEAD", head[:7], "dbfbaa3", tag="[C]", raw=FRONTIER)
    branches = git("branch", "-a", "--format=%(refname:short)").split()
    rec("F.branches_searched", ",".join(branches), tag="[C]", raw=FRONTIER)
    for s in ("0.062", "+0.062", "0.0013", "+0.0013"):
        hits = git("log", "--all", "--oneline", "-S", s).strip()
        rec(f"F.git_log_all_S_{s}", hits.replace("\n", " ; ") or "no commits", tag="[C]", raw=FRONTIER)
    hits = git("log", "--all", "--oneline", "-G", r"0\.0013\b|\+0\.062\b").strip()
    rec("F.git_log_all_G", hits.replace("\n", " ; ") or "no commits", tag="[C]", raw=FRONTIER)
    doc = "docs/BASELINE-CHECK-2026-09-29.md"
    tracked = git("ls-files", "--error-unmatch", doc).strip()
    rec("F.source_doc_tracked", "yes" if tracked else "no (untracked)", tag="[C]", raw=f"{FRONTIER}/{doc}",
        note=f"numbers stated at {doc}:201-202 (and :280)")
    E1, E1B = "experiments/exp1_bands/logs", "experiments/exp1_bands/logs_hotpot_100"
    pil = json.load(open(f"{FRONTIER}/{E1}/static_frontier_0_pilot/test_eval.json"))
    base_test = float(np.mean(pil["per_instance_f1"]))
    cells, files = [], []
    for root, arms in ((E1, ["random", "static_easy", "static_frontier", "static_hard", "vanilla_coupled_gepa"]),
                       (E1B, ["static_easy", "static_frontier", "static_hard"])):
        for arm in arms:
            for s in range(3):
                cd = f"{root}/{arm}_{s}"
                files += [f"{cd}/run_log.txt", f"{cd}/test_eval.json"]
                seed_val, cand = None, {}
                pend = None
                for l in open(f"{FRONTIER}/{cd}/run_log.txt"):        # BASELINE-CHECK Appendix parse()
                    mm = re.search(r"Base program full valset score: ([\d.]+)", l)
                    if mm: seed_val = float(mm.group(1))
                    mm = re.search(r"Individual valset scores for new program: (\{.*\})", l)
                    if mm: pend = float(np.mean(list(ast.literal_eval(mm.group(1)).values())))
                    mm = re.search(r"New program candidate index: (\d+)", l)
                    if mm and pend is not None: cand[int(mm.group(1))] = pend; pend = None
                vals = [cand[k] for k in sorted(cand)]
                te = json.load(open(f"{FRONTIER}/{cd}/test_eval.json"))
                cs = json.load(open(f"{FRONTIER}/{cd}/cell_summary.json"))
                if vals:
                    assert abs(max(vals + [seed_val]) - cs["best_val_f1"]) < 1e-12
                cells.append(dict(cell=cd, seed_val=seed_val, n_acc=len(vals), vals=vals,
                                  test=float(np.mean(te["per_instance_f1"]))))
    untracked = [f for f in files if not git("ls-files", "--error-unmatch", f).strip()]
    rec("F.per_run_files_untracked", len(untracked), 0, tag="[C]", raw=FRONTIER, note=f"{len(files)} files checked")
    seedv = {c["seed_val"] for c in cells}
    rec("F.seed_val_f1_75", seedv.pop() if len(seedv) == 1 else "varies", "0.5963", tag="[C]", raw=f"{FRONTIER}/{E1}/*/run_log.txt:1")
    rec("F.seed_test_f1_300", base_test, "0.6316", tag="[C]", raw=f"{FRONTIER}/{E1}/static_frontier_0_pilot/test_eval.json")
    act = [c for c in cells if c["n_acc"] > 0]
    vg = [max(c["vals"]) - c["seed_val"] for c in act]
    tg = [c["test"] - base_test for c in act]
    rec("F.cells_with_accept", len(act), 21, tag="[C]", raw=FRONTIER)
    rec("F.mean_best_val_gain", float(np.mean(vg)), "0.062", tag="[C]", raw=FRONTIER,
        note="per cell: max accepted-candidate D_pareto F1 (75 items, the returned-program selection set) minus seed; mean over cells")
    rec("F.best_val_gain_min", min(vg), "0.021", tag="[C]", raw=FRONTIER)
    rec("F.best_val_gain_max", max(vg), "0.106", tag="[C]", raw=FRONTIER)
    rec("F.mean_test_gain", float(np.mean(tg)), "0.0013", tag="[C]", raw=FRONTIER,
        note="per cell: returned program's test F1 (300 items) minus seed's; mean over the same cells")
    rec("F.cells_above_seed_on_test", sum(x > 0 for x in tg), 11, tag="[C]", raw=FRONTIER)
    allv = [v - c["seed_val"] for c in act for v in c["vals"]]
    rec("F.accepted_above_seed_on_val", f"{sum(x > 0 for x in allv)}/{len(allv)}", "107/134", tag="[C]", raw=FRONTIER)
    rec("F.median_accepted_val_gain", float(np.median(allv)), "0.027", tag="[C]", raw=FRONTIER)


# ---------------------------------------------------------------- Part R: revision numbers (post review, 2026-10-17)

def _sd1(xs):
    return _mean_sd([float(x) for x in xs])[1]


def _t_ci(xs):
    """Mean and 95% t-interval (df n-1) of a list of floats."""
    n = len(xs); mu, sd = _mean_sd([float(x) for x in xs])
    h = t_ppf(0.975, n - 1) * sd / math.sqrt(n)
    return mu, mu - h, mu + h


def _b3_label(r):
    return "s" + r["run"].split("_seed")[1].split("_")[0]


def r1_hover_gepa_gain():
    raw = f"{SD_RUNS}/B_seed*/endpoints.json; {OUT}/d2_seed_prompt_runs.csv"
    a = [json.load(open(f"{SD_RUNS}/B_seed{s}/endpoints.json"))["endpoint_test_mean"] for s in range(8)]
    b = [float(r["endpoint_test_mean"]) for r in csv.DictReader(open(f"{OUT}/d2_seed_prompt_runs.csv"))]
    assert len(a) == 8 and len(b) == 5
    (ma, sa), (mb, sb) = _mean_sd(a), _mean_sd(b)
    va, vb = sa ** 2 / 8, sb ** 2 / 5
    se = math.sqrt(va + vb)
    df = (va + vb) ** 2 / (va ** 2 / 7 + vb ** 2 / 4)
    diff = ma - mb
    h = t_ppf(0.975, df) * se
    note = "Welch two-sample t, 8 arm-B runs vs the 5 runs that returned the seed prompt; t from t_ppf/t_cdf (stdlib)"
    rec("R1.hover_gepa_gain", diff, "+0.0241", tag="[C]", raw=raw, note=note)
    rec("R1.hover_gepa_gain_ci95_lo", diff - h, "-0.0015", tag="[C]", raw=raw, note=note)
    rec("R1.hover_gepa_gain_ci95_hi", diff + h, "+0.0496", tag="[C]", raw=raw, note=note)
    rec("R1.hover_gepa_gain_p_two_sided", 2 * (1 - t_cdf(abs(diff / se), df)), "0.0622", tag="[C]", raw=raw, note=note)
    rec("R1.hover_gepa_gain_welch_df", df, "9.69", tag="[C]", raw=raw, note=note)


def r2_kept_gain_t(info, src):
    b3 = [r for r in info if r["b"] == 3]
    refs = {"s0": "+0.0074", "s1": "-0.0038", "s2": "-0.0041", "s3": "-0.0030",
            "s4": "+0.0031", "s5": "-0.0011", "s6": "+0.0014", "s7": "+0.0090"}
    means = []
    for r in b3:
        d = [r["ex"][i] - r["ex"][r["acc"][i]["parent_ids"][0]] for i in sorted(r["acc"])]   # N2's d, per run
        m = float(sum(d) / len(d)); means.append(m)
        rec(f"R2.run_mean_child_minus_parent_{_b3_label(r)}", m, refs[_b3_label(r)], tag="[C]", raw=src,
            note=f"{len(d)} kept children (N2's d)")
    assert len(means) == 8
    mu, lo, hi = _t_ci(means)
    note = "t-interval over the 8 run means, df 7, t from t_ppf (stdlib)"
    rec("R2.mean_of_run_means", mu, "+0.0011", tag="[C]", raw=src, note=note)
    rec("R2.ci95_lo_t_run_means", lo, "-0.0031", tag="[C]", raw=src, note=note)
    rec("R2.ci95_hi_t_run_means", hi, "+0.0053", tag="[C]", raw=src, note=note)


def r3_val_noise(info, src):
    ids = sorted(info[0]["val0"], key=str)
    assert len(info) == 10 and len(ids) == 150 and all(sorted(r["val0"], key=str) == ids for r in info)
    var = [_sd1([r["val0"][k] for r in info]) ** 2 for k in ids]
    pooled = math.sqrt(sum(var)) / 150
    rec("R3.pooled_sd_of_150_item_mean", pooled, "0.0132", tag="[C]", raw=src,
        note="per-item variance across the 10 seed-prompt evaluations (ddof 1); sqrt(sum)/150")
    n1 = _sd1([r["ex"][0] for r in info])                 # N1's run-level sd
    b3 = [r for r in info if r["b"] == 3]
    d = [float(r["ex"][i] - r["ex"][r["acc"][i]["parent_ids"][0]]) for r in b3 for i in sorted(r["acc"])]
    assert len(d) == 115
    rec("R3.sd_of_115_d_ddof1", _sd1(d), "0.021", tag="[C]", raw=src,
        note="brief's 4-dp reference was cut off in the paste; checked against the post's 0.021")
    for lab, s, ref_t, ref_n in (("pooled", pooled, "0.0187", 71), ("run_level_N1", n1, "0.0214", 80)):
        thr = math.sqrt(2) * s
        k = sum(abs(x) < thr for x in d)
        rec(f"R3.sqrt2_x_{lab}_sd", thr, ref_t, tag="[C]", raw=src, note="sd of a difference of two independent scorings")
        rec(f"R3.n_abs_d_below_sqrt2_x_{lab}_sd", k, ref_n, tag="[C]", raw=src)
        rec(f"R3.share_abs_d_below_sqrt2_x_{lab}_sd", k / len(d), f"{ref_n / 115:.4f}", tag="[C]", raw=src,
            note=f"{k}/115")


def r4_parent_rescore(info, rows):
    src = "logs/baseline_seed*_b3_*.jsonl (8 runs) + " + IFB
    logged, checked, agree = {}, 0, 0
    for r in [r for r in info if r["b"] == 3]:
        sel = {e["iteration"]: e["candidate_idx"] for e in r["ev"] if e["event"] == "candidate_selected"}
        first = {}
        for e in r["ev"]:
            if e["event"] == "evaluation_end" and e["iteration"] not in first:
                first[e["iteration"]] = e
        for it, cidx in sel.items():
            checked += 1
            agree += first[it]["candidate_idx"] == cidx
            logged[f"{_b3_label(r)}_it{it}"] = sum(first[it]["scores"])
    rec("R4.first_evaluation_end_is_selected_parent", f"{agree}/{checked}", "397/397", tag="[C]", raw=src,
        note="first evaluation_end per b=3 iteration has candidate_selected's candidate_idx")
    fresh = {}
    for r in rows:
        assert fresh.setdefault(r["B_id"], r["parent_B_sum"]) == r["parent_B_sum"]
    assert len(fresh) == 382

    def g60(x):
        k = round(x * 60); assert abs(x * 60 - k) < 0.01, x; return k
    diff = [g60(fresh[b]) - g60(logged[b]) for b in sorted(fresh)]
    n = len(diff)
    rec("R4.n_pairs", n, 382, tag="[C]", raw=src)
    for lab, k, ref_n, ref_s in (("ties", sum(x == 0 for x in diff), 174, "0.4555"),
                                 ("fresh_above_logged", sum(x > 0 for x in diff), 103, "0.2696"),
                                 ("fresh_below_logged", sum(x < 0 for x in diff), 105, "0.2749")):
        rec(f"R4.{lab}_n", k, ref_n, tag="[C]", raw=src, note="on the 1/60 grid (calls.csv is rounded to 4 dp)")
        rec(f"R4.{lab}_share", k / n, ref_s, tag="[C]", raw=src, note=f"{k}/{n}")
    rec("R4.mean_fresh_minus_logged", sum(diff) / 60 / n, "+0.0159", tag="[C]", raw=src, note="batch total, 0-3 scale")
    rec("R4.sd_fresh_minus_logged_ddof1", _sd1([x / 60 for x in diff]), "0.4115", tag="[C]", raw=src)


def r5_own_margin(rows, hrows):
    k60 = [round(r["own_m"] * 60) for r in rows]
    assert all(abs(r["own_m"] * 60 - k) < 0.01 for r, k in zip(rows, k60))
    for lab, sel, ref_n, ref_s in (("above", lambda k: k > 0, 789, "0.3442"), ("tie", lambda k: k == 0, 769, "0.3355"),
                                   ("below", lambda k: k < 0, 734, "0.3202")):
        k = sum(map(sel, k60))
        rec(f"R5.ifb_own_margin_{lab}_n", k, ref_n, tag="[C]", raw=IFB, note="R_B: margin_on_B, R_Bp: margin_on_Bp; 1/60 grid")
        rec(f"R5.ifb_own_margin_{lab}_share", k / len(k60), ref_s, tag="[C]", raw=IFB, note=f"{k}/{len(k60)}")
    rec("R5.ifb_own_margin_mean", sum(k60) / 60 / len(k60), "+0.0043", tag="[C]", raw=IFB, note="batch total, 0-3")
    rec("R5.ifb_own_margin_sd_ddof1", _sd1([k / 60 for k in k60]), "0.4351", tag="[C]", raw=IFB)
    raw = f"{HOVER_PAIRS}/*/draws.jsonl"
    own = [r["margin_on_A"] if r["arm"] == "SAME" else r["margin_on_B"] for r in hrows]   # integer thirds
    assert len(own) == 1458
    for lab, sel, ref_n, ref_s in (("above", lambda k: k > 0, 544, "0.3731"), ("tie", lambda k: k == 0, 515, "0.3532"),
                                   ("below", lambda k: k < 0, 399, "0.2737")):
        k = sum(map(sel, own))
        rec(f"R5.hover_own_margin_{lab}_n", k, ref_n, tag="[C]", raw=raw,
            note="SAME on A_e vs A_e_parent_scores_logged; SWAP on B_e vs B_e_parent_scores_fresh; exact thirds")
        rec(f"R5.hover_own_margin_{lab}_share", k / len(own), ref_s, tag="[C]", raw=raw, note=f"{k}/{len(own)}")
    rec("R5.hover_own_margin_mean", sum(own) / 3 / len(own), "+0.0444", tag="[C]", raw=raw, note="batch total, 0-3")


def r6_cited():
    vals = {v["id"]: v["value"] for v in VALUES}
    rec("R6.screen_familywise_p", int(vals["E1.perms_with_survivor_abs_beta_ge_obs"]) / 200, "0.215", tag="[C]", raw=PERM,
        note="43/200 shuffles with a survivor at least as strong (E1/E3)")
    for id_, path, ln, needle in (
            ("R6.ifb_swap_specificity_naive_pair_ci", "analysis/ablation/batch_swap_v2/results.md", 8, "[-0.0149,+0.0257]"),
            ("R6.hover_swap_specificity_naive_pair_ci", "analysis/ablation/hover_swap/results.md", 11, "[+0.0048, +0.0501]"),
            ("R6.hover_swap_transfer_naive_pair_ci", "analysis/ablation/hover_swap/results.md", 12, "[-0.0149, +0.0489]"),
            ("R6.ablation_gate_margin_deltas", "analysis/ablation/results.md", 39,
             "Δ(i−ii)=−0.016 (p=0.64), Δ(i−iii)=−0.013 (p=0.71)"),
            ("R6.ablation_same_arm_repeat_flips", "analysis/ablation/results.md", 44, "32%"),
            ("R6.best_of_3_own_margin", "analysis/verification_postswap.md", 16, "+0.2298"),
            ("R6.best_of_3_selection_lift", "analysis/verification_postswap.md", 17, "+0.0059"),
            ("R6.best_of_3_selection_lift_ci", "analysis/verification_postswap.md", 18, "[-0.0059, +0.0201]")):
        line = open(path).read().split("\n")[ln - 1]
        rec(id_, needle if needle in line else "NOT FOUND", needle, tag="cited", cited=f"{path}:{ln}",
            note="cited, not recomputed")


def r7_setups():
    ifb = {(c["n_train"], c["n_val"], c["max_metric_calls"], c["gepa_version"]) for _, c in ifb_runs()}
    assert len(ifb) == 1
    ifb = ifb.pop()
    for nm, v, ref in zip(("n_train", "n_val", "max_metric_calls", "gepa_version"), ifb, (150, 150, 2500, "0.1.1")):
        rec(f"R7.ifb_{nm}", v, ref, tag="[C]", raw="logs/baseline_seed*_b*.config.json (10 study runs)")
    runs = sd_runs()
    hv = {tuple(json.load(open(f"{d}/config.json"))[k] for k in ("n_train", "n_val", "max_metric_calls", "gepa_version"))
          for _, d in runs.values()}
    sp = {(e["selection_split"]["n"], e["test_split"]["n"]) for e, _ in runs.values()}
    assert len(hv) == 1 and len(sp) == 1
    for nm, v, ref in zip(("n_train", "n_val", "max_metric_calls", "gepa_version", "selection_n", "test_n"),
                          hv.pop() + sp.pop(), (100, 10, 300, "0.0.27", 50, 150)):
        rec(f"R7.hover_three_arm_{nm}", v, ref, tag="[C]", raw=f"{SD_RUNS}/*_seed*/config.json, endpoints.json",
            cited="analysis/state_dep/results.md:141-146")
    st = {tuple(json.load(open(f"scratch/hover_stage1/stage1_seed{s}/run_summary.json"))[k] for k in ("mm", "n_train", "n_val"))
          for s in range(8)}
    assert len(st) == 1
    for nm, v, ref in zip(("max_metric_calls", "n_train", "n_val"), st.pop(), (None, 100, 10)):
        rec(f"R7.hover_stage1_{nm}", v, ref, tag="[C]", raw="scratch/hover_stage1/stage1_seed*/run_summary.json")
    py = open("scratch/hover_stage1/run_seeds.sh").read().split("\n")[6]
    dist = sorted(glob.glob("scratch/hover_probe/.venv/lib/python3*/site-packages/gepa-*.dist-info"))
    rec("R7.hover_stage1_gepa_version", "not recorded; implied " + dist[0].split("gepa-")[1].split(".dist")[0], tag="[C]",
        raw="scratch/hover_stage1/run_seeds.sh:7 -> scratch/hover_probe/.venv",
        note=f"no run file records a version; run_seeds.sh:7 is {py.strip()!r}")


def r8_exp3_count():
    files = [f for f in git("ls-files", "experiments/exp3_curriculum").split()
             if re.search(r"/seed\d+\.json$", f) and "/smoke/" not in f]
    rec("R8.exp3_runs_committed_non_smoke", len(files), 12, tag="[C]", raw=f"{FRONTIER}/experiments/exp3_curriculum",
        note="4 arms x 3 seeds; git ls-files")
    doc = open(f"{FRONTIER}/docs/BASELINE-CHECK-2026-09-29.md").read().split("\n")
    ok = "Exp 3 has no D_pareto or per-instance test record" in doc[230]
    rec("R8.exp3_no_validation_record", "stated" if ok else "NOT FOUND", "stated", tag="cited",
        cited="docs/BASELINE-CHECK-2026-09-29.md:231-235 (frontier-gepa)")


# ---------------------------------------------------------------- figures (separate venv, reads CSVs only)

OKABE = {"blue": "#0072B2", "orange": "#E69F00", "green": "#009E73", "vermillion": "#D55E00",
         "sky": "#56B4E9", "grey": "#999999", "purple": "#CC79A7"}


def figures():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none", "svg.hashsalt": "article_numbers", "font.family": "DejaVu Sans"})

    def save(fig, name):
        for ext in ("png", "svg"):
            kw = {"dpi": 200} if ext == "png" else {"metadata": {"Date": None}}
            fig.savefig(os.path.join(OUT, f"{name}.{ext}"), bbox_inches="tight", **kw)
        plt.close(fig)

    rd = lambda n: list(csv.DictReader(open(os.path.join(OUT, n))))
    vals = {r["id"]: r for r in rd("values.csv")}

    # fig_gate_headroom
    rows = rd("fig_gate_headroom.csv")
    fig, ax = plt.subplots(figsize=(6, 3.6))
    x = range(len(rows))
    y = [float(r["keep_rate_own"]) for r in rows]
    ax.bar(x, y, color=OKABE["blue"], width=0.7)
    for i, r in zip(x, rows):
        ax.text(i, float(r["keep_rate_own"]) + 0.015, f"n={r['n_own']}", ha="center", fontsize=8)
    ax.set_xticks(list(x), [r["bin"] for r in rows])
    ax.set_xlabel("Parent's score on the batch the rewrite was written from\n(total over 3 examples, 0 to 3)")
    ax.set_ylabel("Share of rewrites kept (own-batch gate)")
    ax.set_ylim(0, max(y) * 1.18)
    ax.text(0.99, 0.97, f"IFBench, {sum(int(r['n_own']) for r in rows):,} rewrites",
            transform=ax.transAxes, ha="right", va="top", fontsize=8, color="#444")
    save(fig, "fig_gate_headroom")

    # fig_screen_null
    mx = [float(r["null_max_beta"]) for r in rd("fig_screen_null.csv")]
    obs = float(vals["E0.observed_beta"]["value"])
    k = int(vals["E2.null_max_ge_observed_beta"]["value"])
    fig, ax = plt.subplots(figsize=(6, 3.6))
    ax.hist(mx, bins=25, color=OKABE["sky"], edgecolor="white")
    ax.axvline(obs, color=OKABE["vermillion"], lw=2)
    ax.text(obs, ax.get_ylim()[1] * 0.95, f"  observed β = {obs:.4f}\n  {k}/{len(mx)} null maxima ≥ observed",
            color=OKABE["vermillion"], va="top", fontsize=8)
    ax.set_xlabel("Strongest effect among 108 rules, per shuffled dataset")
    ax.set_ylabel(f"Shuffled datasets (of n={len(mx)})")
    save(fig, "fig_screen_null")

    # fig_screen_null_survivors
    sv = rd("fig_screen_null_survivors.csv")
    none = sum(r["max_abs_beta"] == "" for r in sv)
    xs = [float(r["max_abs_beta"]) for r in sv if r["max_abs_beta"] != ""]
    k3 = int(vals["E3.perms_survivor_max_abs_beta_ge_obs"]["value"])
    fig, (a0, a1) = plt.subplots(1, 2, figsize=(6.6, 3.6), sharey=True, gridspec_kw={"width_ratios": [1, 6], "wspace": 0.08})
    a0.bar([0], [none], width=0.6, color=OKABE["grey"])
    a0.text(0, none + 1, f"n={none}", ha="center", fontsize=8)
    a0.set_xticks([0], ["no\nsurvivor"])
    a0.set_xlim(-0.6, 0.6)
    a0.set_ylabel(f"Shuffled datasets (of n={len(sv)})")
    w = 0.003
    edges = [obs + w * j for j in range(math.floor((min(xs) - obs) / w), math.ceil((max(xs) - obs) / w) + 1)]
    if edges[-1] <= max(xs):
        edges.append(edges[-1] + w)
    cnt, _, _ = a1.hist(xs, bins=edges, color=OKABE["sky"], edgecolor="white")
    right = sum(c for c, e in zip(cnt, edges[:-1]) if e >= obs - 1e-15)
    assert round(right) == k3, (right, k3)          # bars right of the line are exactly the 43
    a1.axvline(obs, color=OKABE["vermillion"], lw=2)
    a1.text(obs, a1.get_ylim()[1] * 0.97, f"  observed β = {obs:.4f}\n  {k3}/{len(sv)} shuffles ≥ observed",
            color=OKABE["vermillion"], va="top", fontsize=8)
    a1.text(0.99, 0.6, f"{len(xs)} shuffles with ≥1 survivor", transform=a1.transAxes, ha="right", fontsize=8, color="#444")
    a1.spines["left"].set_visible(False); a1.tick_params(left=False)
    a1.set_xlabel("Strongest surviving effect (|β|), per shuffled dataset")
    save(fig, "fig_screen_null_survivors")

    # fig_agreement
    ag = rd("fig_agreement.csv")
    fig, ax = plt.subplots(figsize=(7.4, 3.9))
    w = 0.36
    for i, r in enumerate(ag):
        ax.bar(i - w / 2, float(r["observed"]), w, color=OKABE["blue"], label="observed" if i == 0 else None)
        ax.bar(i + w / 2, float(r["chance"]), w, color=OKABE["grey"], label="expected if independent" if i == 0 else None)
        ax.text(i - w / 2, float(r["observed"]) + 0.01, f"{float(r['observed']):.3f}", ha="center", fontsize=8)
        ax.text(i + w / 2, float(r["chance"]) + 0.01, f"{float(r['chance']):.3f}", ha="center", fontsize=8)
    ax.set_xticks(range(len(ag)), [r["label"].replace(": ", "\n").replace(", ", ",\n") + f"\n(n={r['n']} {r['unit']})"
                                   for r in ag], fontsize=8)
    ax.axvline(1.5, color="#bbb", lw=0.8, ls="--")
    ax.text(0.5, 0.97, "(a) same rewrite, two batches", ha="center", va="top", fontsize=8, transform=ax.get_xaxis_transform())
    ax.text(2.5, 0.97, "(b) siblings, same batch", ha="center", va="top", fontsize=8, transform=ax.get_xaxis_transform())
    ax.set_ylabel("Share of verdict pairs that agree")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False, fontsize=8, loc="upper left", bbox_to_anchor=(0, 0.9))
    save(fig, "fig_agreement")

    # fig_budget, fig_budget_b3
    bud = rd("fig_budget.csv")
    _budget(plt, save, bud, list(dict.fromkeys(r["group"] for r in bud)), "fig_budget", (6.4, 3.6))
    _budget(plt, save, bud, ["b=3 (8 runs)"], "fig_budget_b3", (6.4, 2.0), merge=True,
            ticks=["Three-example batches (8 runs)"])
    print("figures written to", OUT)


def _budget(plt, save, bud, groups, name, size, merge=False, ticks=None):
    if merge:                                        # one segment for validating every kept rewrite
        m = collections.Counter()
        for r in bud:
            c = "validating kept rewrites" if r["category"].startswith("validation: kept") else r["category"]
            m[(r["group"], c)] += int(r["calls"])
        bud = [dict(group=g, category=c, calls=v) for (g, c), v in m.items()]
    cats = list(dict.fromkeys(r["category"] for r in bud))
    colors = ([OKABE["green"], OKABE["blue"], OKABE["grey"]] if merge
              else [OKABE["green"], OKABE["blue"], OKABE["orange"], OKABE["grey"]])
    fig, ax = plt.subplots(figsize=size)
    for gi, g in enumerate(groups):
        left = 0
        tot = sum(int(r["calls"]) for r in bud if r["group"] == g)
        for ci, c in enumerate(cats):
            v = next(int(r["calls"]) for r in bud if r["group"] == g and r["category"] == c)
            ax.barh(gi, v, left=left, color=colors[ci], label=c if gi == 0 else None)
            if v / tot > 0.06:
                ax.text(left + v / 2, gi, f"{v:,}", ha="center", va="center", fontsize=7, color="white")
            left += v
        ax.text(left, gi, f"  {tot:,}", va="center", fontsize=8)
    ax.set_yticks(range(len(groups)), ticks or groups)
    ax.invert_yaxis()
    ax.set_xlabel("Metric calls (task-model evaluations), summed over runs")
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.22 * 3.6 / size[1]), ncol=2)
    save(fig, name)


# ---------------------------------------------------------------- main

def compute():
    assert sys.version_info[:2] == (3, 12)
    os.makedirs(OUT, exist_ok=True)
    print("== A IFBench batch-swap v2"); a0_arm_semantics()
    rows = load_ifb(); a1_opening(rows)
    ifb_cross = a2_cross_batch(rows); ifb_sib = a3_siblings(rows); a4_ties(rows); a5_headroom(rows)
    print("== B HoVer swap")
    m, hrows = load_hover(); hov = b_hover(m, hrows)
    write_csv("fig_agreement.csv", [
        dict(label="IFBench: same rewrite, two batches", observed=repr(ifb_cross["obs"]), chance=repr(ifb_cross["chance"]),
             n=ifb_cross["n"], unit="rewrites"),
        dict(label="HoVer: same rewrite, two batches", observed=repr(hov["obs"]), chance=repr(hov["chance"]),
             n=hov["n"], unit="rewrites"),
        dict(label="IFBench: sibling rewrites, same batch", observed=repr(ifb_sib["obs"]), chance=repr(ifb_sib["chance"]),
             n=ifb_sib["n"], unit="cells of 3"),
        dict(label="HoVer: sibling rewrites, same batch", observed=repr(hov["sib_obs"]), chance=repr(hov["sib_chance"]),
             n=hov["sib_n"], unit="cells of 3"),
    ])
    print("== C IFBench validation cost"); info = c_validation()
    print("== D HoVer three-arm"); d_three_arm()
    print("== E screen calibration"); e_screen()
    print("== X extra draft numbers"); x_ablation(); x_hover_swap(m); x_mde(); x_models(); x_cost()
    print("== F HotpotQA"); f_hotpot()
    print("== R revision numbers")
    src = "logs/baseline_seed*_b*.jsonl (10 runs, article_todos:442-447)"
    r1_hover_gepa_gain(); r2_kept_gain_t(info, src); r3_val_noise(info, src); r4_parent_rescore(info, rows)
    r5_own_margin(rows, hrows); r6_cited(); r7_setups(); r8_exp3_count()
    write_csv("values.csv", VALUES)
    mism = [v["id"] for v in VALUES if v["status"] == "MISMATCH"]
    print(f"\n{len(VALUES)} values; {sum(v['status'] == 'MATCH' for v in VALUES)} MATCH; {len(mism)} MISMATCH: {mism}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["compute", "figures"])
    a = ap.parse_args()
    compute() if a.cmd == "compute" else figures()
