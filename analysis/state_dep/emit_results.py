"""Emit analysis/state_dep/results.md: numbers only, no interpretation.

$0. No LM calls, no network. Read-only over experiment artifacts.

WHAT THIS IS NOT. It writes no prose characterizing any result -- no verdicts, no "suggests" or
"indicates", no grid-cell assignment, no comparison of a p-value to alpha, no statement about
whether any contrast exceeds the MDE. Contrast means and the MDE are printed as bare numbers side
by side; the reading is the analyst's, against v2 §9. If a sentence here would characterize a
result rather than name a quantity, it does not belong in this file.

ORDERING DISCIPLINE. v2 §11-2 requires the MDE and the framing label to be recorded in plan.md §2
BEFORE results.md is read. This script does not enforce that -- nothing does -- and it deliberately
does not read plan.md to check. It is the emitter, not the gate.

VERIFICATION, before a single byte is written:
  * exactly 24 non-smoke endpoints.json, 8 per arm, seeds 0-7 present in all three arms
  * every endpoint_test_mean re-derived from its own 150-element endpoint_test_scores vector
  * every contrast computed twice, by paths that do not share a source, agreeing to 1e-12
Any mismatch raises before the file is opened. A partial table is worse than no table.

  .venv-armT/bin/python analysis/state_dep/emit_results.py
"""
from __future__ import annotations

import datetime as dt
import hashlib
import itertools
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "runs")
OUT = os.path.join(HERE, "results.md")
MANIFEST = os.path.join(HERE, "splits_manifest.json")

ARMS = ("B", "C", "T")
SEEDS = tuple(range(8))
N_TEST = 150

# v2 §11-2, computed by mde_sim.py from the Stage-1 backfill endpoints at D = 1.4431827353722393.
# Printed beside each contrast mean as a bare number. The simulator's sha256 is in Provenance so the
# figure is traceable rather than asserted.
MDE_ENDPOINT = 0.06332

BOOT_REPS = 10000
BOOT_SEED = 20260709  # the project's frozen analysis seed (mde_sim.py:81, dose_control's sample)

# Contrast order is fixed here, not discovered: the C-B anomaly overlay leads the file.
CONTRASTS = (("C", "B"), ("T", "C"), ("T", "B"))


# ----------------------------------------------------------------- load + verify
def load_runs() -> tuple[dict, dict, dict]:
    """Return (stored, recomputed, meta). Two mean tables from two sources in the same file."""
    stored, recomputed, meta = {}, {}, {}
    found = []
    for d in sorted(os.listdir(RUNS)):
        if d.startswith("smoke"):
            continue
        p = os.path.join(RUNS, d, "endpoints.json")
        if not os.path.exists(p):
            continue
        found.append(d)
        b = json.load(open(p))
        arm, seed = b["arm"], int(b["seed"])
        scores = b["endpoint_test_scores"]
        if len(scores) != N_TEST:
            raise SystemExit(f"FAIL {d}: endpoint_test_scores has {len(scores)}, expected {N_TEST}")
        stored[(arm, seed)] = float(b["endpoint_test_mean"])
        recomputed[(arm, seed)] = sum(float(v) for v in scores.values()) / len(scores)
        meta[(arm, seed)] = {
            "run": b["run"], "n_candidates": b["n_candidates"], "sel_best_idx": b["sel_best_idx"],
            "sel_sha": b["selection_split"]["sha256"], "test_sha": b["test_split"]["sha256"],
            "mtime": dt.datetime.fromtimestamp(os.path.getmtime(p)).isoformat(timespec="seconds"),
            "path": os.path.relpath(p, HERE),
        }
    if len(found) != 24:
        raise SystemExit(f"FAIL: {len(found)} non-smoke endpoints.json, expected 24 -> {found}")
    for arm in ARMS:
        got = sorted(s for (a, s) in stored if a == arm)
        if got != list(SEEDS):
            raise SystemExit(f"FAIL arm {arm}: seeds {got}, expected {list(SEEDS)}")
    # the proxy-substitution guard: the stored scalar must equal its own per-example vector
    for k in sorted(stored):
        if abs(stored[k] - recomputed[k]) > 1e-12:
            raise SystemExit(
                f"FAIL {k}: endpoint_test_mean={stored[k]!r} != mean(endpoint_test_scores)="
                f"{recomputed[k]!r}  delta={stored[k] - recomputed[k]:.3e}")
    shas = {(m["sel_sha"], m["test_sha"]) for m in meta.values()}
    if len(shas) != 1:
        raise SystemExit(f"FAIL: run dirs disagree on split sha256 -> {shas}")
    return stored, recomputed, meta


# ----------------------------------------------------------------- statistics, two paths each
def signflip_p_itertools(diffs) -> float:
    """Exact two-sided sign-flip over all 2^n patterns. Mirrors mde_sim.py:39-45."""
    d = np.asarray(diffs, dtype=float)
    obs = abs(d.mean())
    signs = np.array(list(itertools.product([-1.0, 1.0], repeat=len(d))))
    null = np.abs((signs * d).mean(axis=1))
    return float((null >= obs - 1e-12).mean())


def signflip_p_bitmask(diffs) -> float:
    """Same test, independent construction: enumerate sign patterns as integer bitmasks, pure Python."""
    d = [float(x) for x in diffs]
    n = len(d)
    obs = abs(sum(d) / n)
    hits = 0
    for mask in range(1 << n):
        tot = 0.0
        for i in range(n):
            tot += -d[i] if (mask >> i) & 1 else d[i]
        if abs(tot / n) >= obs - 1e-12:
            hits += 1
    return hits / (1 << n)


def boot_ci_numpy(diffs, idx) -> tuple[float, float]:
    d = np.asarray(diffs, dtype=float)
    means = d[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def boot_ci_python(diffs, idx) -> tuple[float, float]:
    """Same resamples, independent aggregation: pure-Python means + nearest-rank percentile."""
    d = [float(x) for x in diffs]
    means = sorted(sum(d[j] for j in row) / len(row) for row in idx.tolist())
    n = len(means)

    def pct(q):  # linear interpolation, matching np.percentile's default
        pos = q / 100.0 * (n - 1)
        lo = int(pos)
        hi = min(lo + 1, n - 1)
        return means[lo] + (means[hi] - means[lo]) * (pos - lo)

    return pct(2.5), pct(97.5)


def contrast(a_vals, b_vals, idx) -> dict:
    diffs = [a - b for a, b in zip(a_vals, b_vals)]
    p1, p2 = signflip_p_itertools(diffs), signflip_p_bitmask(diffs)
    if abs(p1 - p2) > 1e-12:
        raise SystemExit(f"FAIL second-path sign-flip: {p1!r} vs {p2!r}")
    c1, c2 = boot_ci_numpy(diffs, idx), boot_ci_python(diffs, idx)
    if abs(c1[0] - c2[0]) > 1e-12 or abs(c1[1] - c2[1]) > 1e-12:
        raise SystemExit(f"FAIL second-path bootstrap CI: {c1!r} vs {c2!r}")
    m1 = float(np.mean(diffs))
    m2 = sum(diffs) / len(diffs)
    if abs(m1 - m2) > 1e-12:
        raise SystemExit(f"FAIL second-path paired mean: {m1!r} vs {m2!r}")
    return {"diffs": diffs, "mean": m1, "p": p1, "lo": c1[0], "hi": c1[1]}


def main() -> int:
    stored, recomputed, meta = load_runs()
    rng = np.random.default_rng(BOOT_SEED)
    idx = rng.integers(0, len(SEEDS), size=(BOOT_REPS, len(SEEDS)))

    checks = [f"24 endpoint files, 8 per arm, seeds {list(SEEDS)} present in B, C, T",
              "endpoint_test_mean == mean(endpoint_test_scores) for all 24, |delta| <= 1e-12",
              "split sha256 identical across all 24 run dirs"]

    results = {}
    for hi_arm, lo_arm in CONTRASTS:
        # PATH 1 from the stored scalars, PATH 2 from the vector-recomputed means
        a1 = [stored[(hi_arm, s)] for s in SEEDS]
        b1 = [stored[(lo_arm, s)] for s in SEEDS]
        a2 = [recomputed[(hi_arm, s)] for s in SEEDS]
        b2 = [recomputed[(lo_arm, s)] for s in SEEDS]
        r1 = contrast(a1, b1, idx)
        r2 = contrast(a2, b2, idx)
        for f in ("mean", "p", "lo", "hi"):
            if abs(r1[f] - r2[f]) > 1e-12:
                raise SystemExit(f"FAIL second-path {hi_arm}-{lo_arm} {f}: {r1[f]!r} vs {r2[f]!r}")
        results[(hi_arm, lo_arm)] = r1
        checks.append(f"{hi_arm}-{lo_arm}: mean/p/CI agree across stored-scalar and "
                      f"vector-recomputed paths, and across two implementations each (<=1e-12)")

    man = json.load(open(MANIFEST))
    cfg = json.load(open(os.path.join(RUNS, "B_seed0", "config.json")))
    any_meta = meta[("B", 0)]
    sim = os.path.join(HERE, "mde_sim.py")
    sim_sha = hashlib.sha256(open(sim, "rb").read()).hexdigest()

    L = []
    w = L.append
    w("# state-dependent novelty selection — results")
    w("")
    w("Numbers only. No interpretation, no verdicts, no grid-cell assignment. Read against v2 §9.")
    w(f"Emitted by `emit_results.py` from {len(stored)} run directories.")
    w("")
    w(f"Endpoint = §8b selection-split argmax, evaluated on the {N_TEST}-claim test split.")
    w("Paired by seed. `p` is the exact two-sided sign-flip over all 2^8 = 256 patterns.")
    w(f"CI is a paired bootstrap, {BOOT_REPS:,} resamples, seed {BOOT_SEED}, percentile method.")
    w(f"MDE (v2 §11-2, endpoint units): {MDE_ENDPOINT}")
    w("")
    w("---")
    w("")

    for n, (hi_arm, lo_arm) in enumerate(CONTRASTS):
        r = results[(hi_arm, lo_arm)]
        tag = "## Anomaly overlay — " if n == 0 else "## Contrast — "
        w(f"{tag}{hi_arm} − {lo_arm}")
        w("")
        w("| seed | " + f"{hi_arm} | {lo_arm} | {hi_arm} − {lo_arm} |")
        w("|---|---|---|---|")
        for i, s in enumerate(SEEDS):
            w(f"| {s} | {stored[(hi_arm, s)]:.6f} | {stored[(lo_arm, s)]:.6f} | {r['diffs'][i]:+.6f} |")
        w("")
        w("| quantity | value |")
        w("|---|---|")
        w(f"| paired mean | {r['mean']:+.6f} |")
        w(f"| MDE (§11-2) | {MDE_ENDPOINT} |")
        w(f"| p (exact two-sided sign-flip) | {r['p']:.6f} |")
        w(f"| bootstrap 95% CI | [{r['lo']:+.6f}, {r['hi']:+.6f}] |")
        w("")

    w("---")
    w("")
    w("## Per-run endpoint scores")
    w("")
    for arm in ARMS:
        w(f"### Arm {arm}")
        w("")
        w("| seed | run | endpoint_test_mean | n_candidates | sel_best_idx |")
        w("|---|---|---|---|---|")
        for s in SEEDS:
            m = meta[(arm, s)]
            w(f"| {s} | `{m['run']}` | {stored[(arm, s)]:.6f} | {m['n_candidates']} | {m['sel_best_idx']} |")
        w("")

    w("## Per-arm mean and SD")
    w("")
    w("| arm | n | mean | SD (ddof=1) |")
    w("|---|---|---|---|")
    for arm in ARMS:
        v = np.array([stored[(arm, s)] for s in SEEDS], dtype=float)
        w(f"| {arm} | {len(v)} | {v.mean():.6f} | {v.std(ddof=1):.6f} |")
    w("")

    w("---")
    w("")
    w("## Provenance")
    w("")
    w("| field | value |")
    w("|---|---|")
    w(f"| run directories read | {len(stored)} (24 non-smoke; smoke excluded) |")
    w(f"| selection split | n={man['selection']['n']} sha256 `{any_meta['sel_sha']}` |")
    w(f"| test split | n={man['test']['n']} sha256 `{any_meta['test_sha']}` |")
    w(f"| gepa version | {cfg['gepa_version']} |")
    w(f"| dspy version | {cfg['dspy_version']} |")
    w(f"| task LM | {cfg['task_lm']} |")
    w(f"| max_metric_calls | {cfg['max_metric_calls']} |")
    w(f"| git commit (run config) | {cfg['git_commit']} |")
    w(f"| design | {cfg['design']} |")
    w(f"| mde_sim.py sha256 | `{sim_sha}` |")
    w(f"| emit_results.py sha256 | `{hashlib.sha256(open(__file__, 'rb').read()).hexdigest()}` |")
    w("")
    w("### endpoints.json mtimes")
    w("")
    w("| run | mtime | path |")
    w("|---|---|---|")
    for arm in ARMS:
        for s in SEEDS:
            m = meta[(arm, s)]
            w(f"| `{m['run']}` | {m['mtime']} | `{m['path']}` |")
    w("")
    w("### verification performed before emission")
    w("")
    for c in checks:
        w(f"- {c}")
    w("")

    body = "\n".join(L) + "\n"
    with open(OUT, "w") as fh:
        fh.write(body)

    rows = sum(1 for ln in L if ln.startswith("| ") and not ln.startswith("|---"))
    print(f"wrote {os.path.relpath(OUT, HERE)}")
    print(f"  lines            : {len(L)}")
    print(f"  table rows        : {rows}")
    print(f"  run dirs read     : {len(stored)}")
    print(f"  checks passed     : {len(checks)}")
    for c in checks:
        print(f"    - {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
