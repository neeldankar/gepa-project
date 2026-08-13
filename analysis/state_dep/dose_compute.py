"""§11-0 dose computation. GATED: APPROVED-dose for the live path (~$3.6).

Two modes run TONIGHT at $0 and need no gate:

  --selftest        validate the order-statistic math (gap definition) on synthetic data
  --pre-estimate    §15-12 degeneracy pre-estimate from the SCREEN's existing 3-member novelty
                    columns in features.csv. Free, and it bounds how much selection room exists.

The live path (--live) needs the 3 unmatched candidates' feedback texts, which do NOT exist on disk
for any of the 243 swap events (see notes/FREEZE.md C1) and must be re-derived by re-executing the
parent. That is real LM spend and is gated.

THE GAP, per review R5(c) and R2 (v2 §11-0):

    For each event, x = the 6 candidates' knn_emb_fb novelties, sorted ASCENDING.

      selected_min = x_(4)          the 4th order statistic ascending
                                    == the 3rd-HIGHEST value
                                    == the min of the top-3-by-novelty subset
                                    == exactly what arm T's selector realizes

      random_min   = (1/20) * sum over all C(6,3)=20 subsets S of min(x_S)
                                    == the expected min of a uniformly random 3-subset
                                    == what arm C realizes in expectation

      gap          = selected_min - random_min

    D_s = mean_{e in seed s} gap_e / sd_s     (each seed in its own within-run SD units)
    D   = mean_s D_s

`sd_s` is the screen's per-run standardization SD (screen_part4_stats.py:62, ddof=0). There is NO
scalar SD_screen: the 8 within-run SDs span [0.021870 .. 0.029460]. Ratified 2026-07-09.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCREEN = os.path.join(REPO, "analysis", "hover_screen")
sys.path.insert(0, HERE)

# Written by dose_control.py ONLY when the within-session reproducibility control clears its
# pre-registered bar; required by live(). Kept in sync with dose_control.PASS_MARKER by path, not
# by import, so this module stays import-clean.
PASS_MARKER = os.path.join(HERE, "markers", "DOSE_CONTROL.PASS")

# Acquisition runs under the venv the swap itself ran on, so library drift is not a variable.
PROBE_PY = os.path.join(REPO, "scratch", "hover_probe", ".venv", "bin", "python")
ACQUIRE = os.path.join(HERE, "dose_acquire.py")
TEXTS = os.path.join(HERE, "dose_texts")
OUT_DOSE = os.path.join(HERE, "dose.json")
SPEND_CAP = 11.00   # v2.2: 235 x 6 + control. NOT $3.61 -- that was v2.1's 705-call line, and it
                    # was fitted at $0.004543/call when the smoke measured §8b at $0.006121.

BETA = 0.0379395028680125  # screen_stats_cells.csv:434, knn_emb_fb_min / spec_i / read 4.1
M, B = 6, 3

# v2.1 §20-2, ratified 2026-07-22: the dose is defined on 235 events, not 243. The 8 ordinal-0
# events have no k=3 archive and no defined novelty, and 235 is the frame BETA above was estimated
# on (verify_novelty.py byte-verified 235/235 against features.csv). Defining D on 243 would put D
# and BETA on different event sets inside the product D x BETA/2 that §11-1 and §11-2 consume.
EVENT_SET = 235

# Per-seed within-run SDs of knn_emb_fb_min (ddof=0), recomputed from features.csv.
SD_PER_SEED = {
    0: 0.02186988, 1: 0.02443303, 2: 0.02946035, 3: 0.02319585,
    4: 0.02871316, 5: 0.02523783, 6: 0.02501051, 7: 0.02653783,
}


def selected_min(x6) -> float:
    """x_(4) ascending == the min of the top-3-by-novelty subset."""
    return float(np.sort(np.asarray(x6, dtype=float))[M - B])


def expected_random_min(x6) -> float:
    """Exact enumeration over all C(6,3)=20 subsets."""
    xs = list(map(float, x6))
    mins = [min(s) for s in itertools.combinations(xs, B)]
    assert len(mins) == 20, len(mins)
    return float(np.mean(mins))


def gap(x6) -> float:
    return selected_min(x6) - expected_random_min(x6)


# --------------------------------------------------------------------------- self-test ($0)
def selftest() -> int:
    print("=== gap() self-test: the order-statistic identity ===")
    rng = np.random.default_rng(20260709)
    ok = True

    # 1. selected_min really is the min of the top-3 subset, and that subset maximizes the min.
    for _ in range(2000):
        x = rng.normal(size=M)
        top3 = np.sort(x)[-B:]
        best = max(min(s) for s in itertools.combinations(map(float, x), B))
        if not (np.isclose(selected_min(x), top3.min()) and np.isclose(selected_min(x), best)):
            ok = False
            print(f"  FAIL on {x}")
            break
    print(f"  selected_min == min(top-3) == max-over-subsets-of-min : {ok}")

    # 2. gap >= 0 always (the selector's min can never be below the average subset min).
    gaps = [gap(rng.normal(size=M)) for _ in range(5000)]
    print(f"  gap >= 0 in all 5000 draws                            : {min(gaps) >= -1e-12}")
    print(f"  mean gap under iid normal                             : {np.mean(gaps):.4f} SD")
    print("    (review R2's ceiling argument: ~1 SD under iid; real novelty scores share an")
    print("     archive and are positively correlated, so the realized D should be well below.)")

    # 3. degenerate case: all six identical -> zero selection room.
    # NB: compare with isclose, not ==. sum(twenty 0.3s)/20 == 0.29999999999999993 in IEEE754, so
    # an exact-equality assertion here fails on a rounding artifact of the TEST, not of gap().
    degenerate = gap([0.3] * 6)
    degenerate_ok = bool(np.isclose(degenerate, 0.0, atol=1e-15))
    print(f"  gap([c]*6) ~= 0 (degenerate, §15-12)                   : {degenerate_ok} "
          f"(gap={degenerate:.3e})")

    # 4. hand-checked example.
    x = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0]
    sm = selected_min(x)  # sorted asc -> index 3 -> 3.0
    rm = expected_random_min(x)
    print(f"  x=0..5 -> selected_min={sm} (expect 3.0), E[rand min]={rm:.4f}, gap={sm - rm:.4f}")
    hand_ok = sm == 3.0 and np.isclose(rm, 0.75)

    ok = bool(ok and degenerate_ok and hand_ok and min(gaps) >= -1e-12)
    print("\nSELFTEST PASS" if ok else "\nSELFTEST FAIL")
    return 0 if ok else 1


# ------------------------------------------------------- degeneracy pre-estimate ($0, real data)
def pre_estimate() -> int:
    """§15-12: how much novelty spread exists within a batch, using the screen's own 3 members.

    This is NOT the dose. The dose needs 6 candidates. But the screen already scored the 3 reflected
    members per event, so the within-event spread over those 3 is a free lower-bound-ish read on
    whether there is anything to select on at all. If the 3-member spread were ~0, the 6-member
    spread would likely be small too and T ~= C by construction.
    """
    rows = list(csv.DictReader(open(os.path.join(SCREEN, "features.csv"))))
    per_seed = {}
    for r in rows:
        if r["knn_emb_fb_min"] == "":
            continue  # ordinal-0, no k=3 archive
        s = int(r["seed"])
        lo, hi = float(r["knn_emb_fb_min"]), float(r["knn_emb_fb_max"])
        sd = float(r["knn_emb_fb_std"])
        per_seed.setdefault(s, []).append((hi - lo, sd, float(r["knn_emb_fb_mean"])))

    print("=== §15-12 degeneracy pre-estimate (3 reflected members per event; NOT the dose) ===")
    print(f"{'seed':>5} {'n':>4} {'mean spread':>13} {'spread/sd_s':>13} {'mean within-ev sd':>19}")
    all_norm = []
    for s in sorted(per_seed):
        v = per_seed[s]
        spread = np.mean([a for a, _, _ in v])
        wsd = np.mean([b for _, b, _ in v])
        norm = spread / SD_PER_SEED[s]
        all_norm.append(norm)
        print(f"{s:>5} {len(v):>4} {spread:>13.6f} {norm:>13.4f} {wsd:>19.6f}")
    print(f"\n  pooled mean (max-min) spread over 3 members, in within-run SD units: "
          f"{np.mean(all_norm):.4f} SD")
    print("  Reading: there IS selection room -- the within-event spread across just 3 members is")
    print("  of the same order as the between-event SD the screen's beta is denominated in. With 6")
    print("  candidates the spread can only grow. This does not estimate D; it rules out the")
    print("  degenerate case where T == C by construction.")
    return 0


# --------------------------------------------------------------------------- novelty scoring
def score_texts(texts_dir: str, which_pass: int = 0) -> dict:
    """Score acquired feedback texts against the screen's archive and return D. $0, no gate.

    Runs under .venv-armT (sentence-transformers). Two deliberate properties:

    ARCHIVE FIDELITY. The archive is the screen's own SAME-arm blocks, encoded in ONE call in the
    screen's interleaved (fb, full) order -- verbatim `verify_novelty.py:68-77`. The 6 candidate
    texts per event are encoded in a SECOND, SEPARATE call. sentence_transformers sorts by length
    inside a batch, so folding the new texts into the archive call would change the archive's
    batch composition and break the byte-verified 235/235 reproduction. Two calls keeps the
    archive bitwise what the screen committed.

    ARCHIVE TIMING. n_arch is snapshotted BEFORE the event's own members are added and the archive
    advances strictly after scoring -- `verify_novelty.py:97-102`. The candidates are scored
    against the archive AS OF that event and never enter it: they are counterfactual draws, not
    reflection objects the run actually produced.
    """
    import numpy as np  # noqa: PLC0415

    sys.path.insert(0, SCREEN)
    from novelty import encode, feedback_text, full_text, knn_novelty, load_embedder  # noqa: PLC0415
    from screen_part0 import parse_si  # noqa: PLC0415

    pairs = os.path.join(REPO, "analysis", "ablation", "hover_swap", "pairs")
    recs = {}
    for fn in sorted(os.listdir(texts_dir)):
        if fn.endswith(".json"):
            r = json.load(open(os.path.join(texts_dir, fn)))
            recs[r["pid"]] = r

    blocks_by_pid = {}
    for pid in sorted(os.listdir(pairs)):
        txt = open(os.path.join(pairs, pid, "reflect_in_SAME.txt"), encoding="utf-8").read()
        blocks_by_pid[pid] = parse_si(txt, pid)

    model = load_embedder()
    keys, texts = [], []
    for pid, blks in blocks_by_pid.items():
        for j, blk in enumerate(blks):
            keys += [(pid, j, "fb"), (pid, j, "full")]
            texts += [feedback_text(blk), full_text(blk)]
    A = encode(model, texts)                      # call 1: the archive, screen-verbatim
    arch = {k: A[i] for i, k in enumerate(keys)}

    ckeys, ctexts = [], []
    for pid, r in recs.items():
        for pos, fb in sorted(r["passes"][which_pass].items(), key=lambda kv: int(kv[0])):
            ckeys.append((pid, int(pos)))
            ctexts.append(fb)
    C = encode(model, ctexts)                     # call 2: the candidates, separately
    cand = {k: C[i] for i, k in enumerate(ckeys)}

    ev_index = json.load(open(os.path.join(SCREEN, "events_index.json")))
    per_event, per_seed = {}, {}
    for seed in range(8):
        evs = sorted([e for e in ev_index.values() if e["seed"] == seed],
                     key=lambda e: e["ordinal"])
        arch_emb, gaps = [], []
        for ev in evs:
            pid = f"seed{seed}_i{ev['trace_i']}"
            n_arch = len(arch_emb)
            if pid in recs:
                x6 = [knn_novelty(cand[(pid, p)], arch_emb if n_arch >= 3 else None)
                      for p in recs[pid]["draw6_pos"]]
                if not any(np.isnan(v) for v in x6):
                    g = gap(x6)
                    per_event[pid] = {"x6": x6, "gap": g, "n_arch": n_arch}
                    gaps.append(g)
            for slot in range(len(blocks_by_pid[pid])):
                arch_emb.append(arch[(pid, slot, "fb")])
        if gaps:
            per_seed[seed] = float(np.mean(gaps)) / SD_PER_SEED[seed]

    D = float(np.mean([per_seed[s] for s in sorted(per_seed)])) if per_seed else float("nan")
    return {"pass": which_pass, "n_events": len(per_event), "D": D,
            "D_per_seed": per_seed, "per_event": per_event}


# --------------------------------------------------------------------------- the live path
def live() -> int:
    from gates import require

    gate = require("APPROVED-dose")

    # v2.2 §11-0 step 1 is an INTERLOCK, not advice. The within-session reproducibility control
    # must have cleared its pre-registered bar before D is computed, because D is a difference of
    # order statistics and is only meaningful if it exceeds this program's own re-execution noise.
    # dose_control.py writes the marker only on a clear; a fail's pre-registered response is to
    # DROP the dose, so a missing marker is a STOP, not something to work around.
    if not os.path.exists(PASS_MARKER):
        raise SystemExit(
            f"\nREFUSING: {os.path.relpath(PASS_MARKER, HERE)} absent.\n"
            "The within-session reproducibility control has not cleared. Run, under this gate:\n"
            "  .venv-armT/bin/python analysis/state_dep/dose_control.py --run\n"
            "It writes the marker only if |D_30(1) - D_30(2)| <= mean(D_30). A fail is a STOP:\n"
            "the pre-registered fallback is to DROP the dose (§11-0), NEVER the biased\n"
            "3-candidate shrink.\n"
        )

    from dose_acquire import event_rows  # noqa: PLC0415  (stdlib-only at import time)

    pids = [r["pair_id"] for r in event_rows()]
    print(f"=== dose live path (v2.2): {len(pids)} events x 6 candidates ===")
    print(f"  acquisition venv : {os.path.relpath(PROBE_PY, REPO)}")
    print(f"  texts            : {os.path.relpath(TEXTS, HERE)}")
    print(f"  spend cap        : ${SPEND_CAP:.2f}")
    print(f"  gate verified    : {gate['sha256'][:16]}...\n")

    rc = subprocess.call([PROBE_PY, "-u", ACQUIRE, "--out", TEXTS, "--passes", "1",
                          "--cap", str(SPEND_CAP)], cwd=REPO)
    if rc != 0:
        print(f"\nacquisition failed (rc={rc}); checkpoints kept, re-running resumes at $0")
        return rc

    print("\n=== scoring against the screen archive (.venv-armT, $0) ===")
    res = score_texts(TEXTS, which_pass=0)
    if res["n_events"] != EVENT_SET:
        print(f"WARNING: scored {res['n_events']} events, expected {EVENT_SET}")
    res["design"] = "state-dependent-design-v2.2-frozen §11-0"
    res["event_set"] = EVENT_SET
    json.dump(res, open(OUT_DOSE, "w"), indent=2)

    print(f"  events scored : {res['n_events']}")
    for s in sorted(res["D_per_seed"]):
        print(f"    seed {s}: D_s = {res['D_per_seed'][s]:.4f}")
    print(f"\n  D = {res['D']:.4f}  (within-run SD units)")
    print(f"  wrote {os.path.basename(OUT_DOSE)}")
    print(f"\n  next: mde_sim.py --endpoints stage1_backfill_endpoints.json --dose {res['D']:.4f}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pre-estimate", action="store_true")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--score-texts", metavar="DIR",
                    help="$0: score already-acquired texts in DIR and print D (no gate, no spend)")
    ap.add_argument("--pass", dest="which_pass", type=int, default=0)
    a = ap.parse_args()
    if a.score_texts:
        r = score_texts(a.score_texts, a.which_pass)
        print(json.dumps({k: v for k, v in r.items() if k != "per_event"}, indent=2))
        raise SystemExit(0)
    if a.selftest:
        raise SystemExit(selftest())
    if a.pre_estimate:
        raise SystemExit(pre_estimate())
    if a.live:
        raise SystemExit(live())
    ap.error("pick one of --selftest / --pre-estimate / --live")
