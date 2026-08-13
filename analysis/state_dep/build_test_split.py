"""Construct the §8a test split AND the §8b selection split. GATED: APPROVED-testsplit (~$3.13).

WHY THIS COSTS MONEY, when the original brief expected $0. Reproducing `stage1_run.py:131-141`
exactly: 245 graded records -> 123 imperfect (recall<1.0) -> 110 consumed by Stage 1 -> **13 remain,
and all 13 have recall == 0.0**. 13 < 100, so §8a's own `N<100 => STOP-and-flag` rule fires. The
remainder is also the hardest tier only: the sort key `(-recall, claim)` consumed all 70 claims at
recall 2/3 and all 35 at 1/3, then 5 of the 18 zeros. A split drawn from it would be maximally
unrepresentative.

So the pool is FRESHLY GRADED claims from `threehop.jsonl` beyond the graded slice. Grading runs the
same 3-hop program via `grade_threehop.py`'s procedure, which calls `dspy.ChainOfThought` on
gpt-4.1-mini -- hence live spend.

ONE PASS, TWO SPLITS (v2.1 §8a second amendment, ratified 2026-07-22):

    frame        threehop_idx 295..994 -- a FIXED 700-claim frame, graded in full
    cost         700 x $0.00447/claim  ~=  $3.13     (measured rate, graded_summary.json)
    expected     ~351 imperfect at the observed rate 123/245 = 0.502
    draw order   test FIRST (N=150, random.Random(20260709)), THEN selection (N=50,
                 random.Random(20260710)) from what remains. BINDING: reversing it yields
                 different splits from the same seeds.

The frame is fixed rather than "grade until 200 imperfect" on purpose: a stopping rule on the
imperfect count makes the sampling frame endogenous to the grades. A fixed frame is exogenous, and
it is what the seeded draws sample from.

Disjointness from Stage-1's train (100) and val (10) is automatic -- those live in threehop_idx
50..294 -- and is asserted anyway. Both splits are committed as JSON with their sha256s BEFORE any
test or selection evaluation exists (§8a, §8b).

    dry run (no gate, no spend, prints both split plans):
        analysis/state_dep/.venv-armT/bin/python analysis/state_dep/build_test_split.py --dry-run
    live (requires the gate):
        analysis/state_dep/.venv-armT/bin/python analysis/state_dep/build_test_split.py
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from gates import require  # noqa: E402

GRADED = os.path.join(REPO, "scratch", "hover_stage1", "graded_records.jsonl")
OUT_POOL = os.path.join(HERE, "test_pool_graded.jsonl")
OUT_POOL_SUMMARY = os.path.join(HERE, "test_pool_summary.json")
OUT_TEST = os.path.join(HERE, "test_split.json")
OUT_SELECTION = os.path.join(HERE, "selection_split.json")
OUT_MANIFEST = os.path.join(HERE, "splits_manifest.json")

# ---- pre-registered constants (v2.1 §8a, §8b). Do not tune. -------------------------------------
START_IDX = 295         # first ungraded threehop index (graded file spans 50..294 contiguous)
N_GRADE = 700           # fixed frame: 295..994
TEST_SEED = 20260709
TEST_N = 150
TEST_MIN_N = 100        # §8a: N < 100 is a STOP-and-flag
SELECTION_SEED = 20260710
SELECTION_N = 50
IMPERFECT_RATE = 123 / 245
USD_PER_CLAIM = 0.00447  # measured, graded_summary.json
SPEND_CAP = 5.00         # hard tripwire; the estimate is ~$3.13
WORKERS = 8
CHUNK = 24


def stage1_consumed() -> set[int]:
    """Reproduce stage1_run.py:131-141 exactly and return the consumed threehop_idx set."""
    recs = [json.loads(line) for line in open(GRADED, "rb")]
    imperfect = [r for r in recs if r["recall"] < 1.0]
    imperfect.sort(key=lambda r: (-r["recall"], r["claim"]))
    need = 100 + 10
    chosen = imperfect[:need] if len(imperfect) >= need else (imperfect * ((need // len(imperfect)) + 1))[:need]
    return {r["threehop_idx"] for r in chosen}


def sha256_of(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def draw_splits(imperfect: list[dict]) -> tuple[list[dict], list[dict]]:
    """The pre-registered draw: test first, then selection from the remainder.

    Both are uniform samples without replacement from a pool held in ascending `threehop_idx`
    order, so the draw is a pure function of (pool contents, seed) and not of grading order.
    """
    pool = sorted(imperfect, key=lambda r: r["threehop_idx"])
    if len(pool) < TEST_MIN_N:
        raise SystemExit(
            f"STOP-and-flag (§8a): only {len(pool)} imperfect claims in the frame, need >= {TEST_MIN_N}."
        )
    n_test = min(TEST_N, len(pool))
    if n_test < TEST_N:
        print(f"  NOTE: pool {len(pool)} < {TEST_N}; test split takes all remaining (§8a), N={n_test}")
    test = random.Random(TEST_SEED).sample(pool, n_test)

    test_ids = {r["threehop_idx"] for r in test}
    rest = [r for r in pool if r["threehop_idx"] not in test_ids]
    if len(rest) < SELECTION_N:
        raise SystemExit(
            f"STOP-and-flag (§8b): {len(rest)} imperfect claims remain after the test draw, "
            f"need {SELECTION_N}. The selection split is NOT silently shrunk."
        )
    selection = random.Random(SELECTION_SEED).sample(rest, SELECTION_N)
    return test, selection


def commit_split(path: str, name: str, seed: int, recs: list[dict], pool_n: int, consumed: set[int]) -> dict:
    """Write a split artifact and return its provenance record (with sha256)."""
    ids = sorted(r["threehop_idx"] for r in recs)
    assert not (set(ids) & consumed), f"{name} split overlaps Stage-1's consumed 110 — impossible, STOP"
    assert min(ids) >= START_IDX, f"{name} split contains a claim from the old graded slice — STOP"
    blob = {
        "split": name,
        "design": "state-dependent-design-v2.1-frozen §8a (test) / §8b (selection)",
        "seed": seed,
        "n": len(recs),
        "frame": {"start_idx": START_IDX, "n_graded": N_GRADE, "imperfect_pool": pool_n},
        "draw": "uniform without replacement, random.Random(seed).sample(pool sorted by threehop_idx)",
        "threehop_ids": ids,
        "claims": [
            {"threehop_idx": r["threehop_idx"], "claim": r["claim"], "gold": r["gold"],
             "grader_recall": r["recall"]}
            for r in sorted(recs, key=lambda r: r["threehop_idx"])
        ],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(blob, fh, indent=2, ensure_ascii=False)
    h = sha256_of(path)
    hist = Counter(round(r["recall"], 3) for r in recs)
    print(f"  {name:<9} N={len(recs):<4} sha256={h}")
    print(f"  {'':<9} grader-recall mix: {dict(sorted(hist.items()))}")
    return {"path": os.path.basename(path), "sha256": h, "n": len(recs), "seed": seed}


def grade_frame() -> list[dict]:
    """LIVE. Grade threehop_idx START_IDX .. START_IDX+N_GRADE-1.

    Near-verbatim copy of scratch/hover_stage1/grade_threehop.py's procedure (that file is frozen on
    the do-not list, so its logic is copied rather than imported and mutated). Deltas: START=295,
    a fixed 700-claim frame with NO imperfect-count early stop, and output to test_pool_graded.jsonl.
    """
    sys.path.insert(0, os.path.join(REPO, "scratch", "hover_probe"))
    os.chdir(os.path.join(REPO, "scratch", "hover_probe"))
    import orjson  # noqa: PLC0415
    import probe  # noqa: PLC0415

    import dspy  # noqa: PLC0415

    probe._load_env()
    lm = dspy.LM("openai/gpt-4.1-mini", max_tokens=3000)
    dspy.configure(lm=lm)
    gen_query = dspy.ChainOfThought("claim, notes -> query")
    append_notes = dspy.ChainOfThought("claim, notes, context -> new_notes: list[str], titles: list[str]")

    ex = probe.load_threehop()
    end = min(START_IDX + N_GRADE, len(ex))
    if end - START_IDX < N_GRADE:
        print(f"  NOTE: threehop.jsonl holds {len(ex)} claims; frame truncated to {end - START_IDX}")
    print(f"threehop={len(ex)}; FIXED frame [{START_IDX}:{end}] ({end - START_IDX} claims) cap=${SPEND_CAP}",
          flush=True)

    def spend() -> float:
        tot = 0.0
        for h in list(lm.history):
            u = h.get("usage") or {}
            tot += u.get("prompt_tokens", 0) * probe.PRICE_IN + u.get("completion_tokens", 0) * probe.PRICE_OUT
        return tot

    def grade_one(idx):
        e = ex[idx]
        with dspy.context(lm=lm):
            notes, per_hop = [], []
            for hop in range(probe.NUM_HOPS):
                q = gen_query(claim=e["claim"], notes=notes).query
                ctx = probe.search(q, k=probe.NUM_DOCS)
                rt = [probe.title_of(c) for c in ctx]
                per_hop.append({"hop": hop + 1, "query": q, "retrieved_titles": rt})
                pred = append_notes(claim=e["claim"], notes=notes, context=ctx)
                notes.extend(pred.new_notes if isinstance(pred.new_notes, list) else [str(pred.new_notes)])
        allret = sorted({t for h in per_hop for t in h["retrieved_titles"]})
        gold = e["titles"]
        recall = len(set(gold) & set(allret)) / len(gold) if gold else 0.0
        return {"threehop_idx": idx, "claim": e["claim"], "gold": gold, "per_hop": per_hop,
                "all_retrieved": allret, "missed": sorted(set(gold) - set(allret)),
                "recall": recall, "si": probe.build_si(gold, allret)}

    t0 = time.time()
    out = open(OUT_POOL, "wb")
    wlock = threading.Lock()
    records: list[dict] = []
    n_imperfect = 0

    def commit(rec):
        nonlocal n_imperfect
        with wlock:
            records.append(rec)
            out.write(orjson.dumps(rec) + b"\n")
            out.flush()
            if rec["recall"] < 1.0:
                n_imperfect += 1

    # calibration: 5 claims sequential, measured before the parallel remainder
    for idx in range(START_IDX, min(START_IDX + 5, end)):
        commit(grade_one(idx))
    el, sp = time.time() - t0, spend()
    calib = {"claims": len(records), "elapsed_s": round(el, 2), "spend_usd": round(sp, 4),
             "s_per_claim": round(el / max(1, len(records)), 2),
             "usd_per_claim": round(sp / max(1, len(records)), 5)}
    print(f"[CALIB @{len(records)}] {calib['s_per_claim']}s/claim ${calib['usd_per_claim']}/claim "
          f"-> proj {N_GRADE} claims ${calib['usd_per_claim'] * N_GRADE:.2f}, "
          f"parallel x{WORKERS} ~{calib['s_per_claim'] * N_GRADE / WORKERS / 60:.0f}min", flush=True)

    rest = list(range(START_IDX + len(records), end))
    stopped = None
    with ThreadPoolExecutor(max_workers=WORKERS) as exsvc:
        for c0 in range(0, len(rest), CHUNK):
            if spend() > SPEND_CAP:
                stopped = "cap"
                break
            for rec in exsvc.map(grade_one, rest[c0:c0 + CHUNK]):
                commit(rec)
            print(f"  graded={len(records)} imperfect={n_imperfect} ${spend():.4f} "
                  f"{(time.time() - t0) / 60:.1f}min", flush=True)
    out.close()

    actual, elapsed = spend(), time.time() - t0
    summary = {
        "frame_start": START_IDX, "frame_end": end, "graded": len(records),
        "imperfect": n_imperfect, "perfect": len(records) - n_imperfect,
        "spend_usd": round(actual, 4), "usd_per_claim": round(actual / max(1, len(records)), 5),
        "elapsed_s": round(elapsed, 1), "stopped_reason": stopped or "frame_exhausted",
        "calibration_at_5": calib,
        "recall_hist": {str(round(k, 3)): v
                        for k, v in sorted(Counter(round(r["recall"], 3) for r in records).items())},
    }
    json.dump(summary, open(OUT_POOL_SUMMARY, "w"), indent=2)
    print(f"\ngraded {len(records)} -> {n_imperfect} imperfect  ${actual:.4f}  {elapsed / 60:.1f}min",
          flush=True)
    if stopped == "cap":
        raise SystemExit(f"SPEND CAP ${SPEND_CAP} hit after {len(records)} claims — STOP, Neel decides.")
    return records


def selftest() -> int:
    """$0: prove the draw is deterministic, disjoint, and order-dependent as pre-registered."""
    pool = [{"threehop_idx": START_IDX + i, "claim": f"c{i}", "gold": ["g"], "recall": 0.5}
            for i in range(351)]  # the expected imperfect yield of a 700-claim frame
    a_test, a_sel = draw_splits(pool)
    b_test, b_sel = draw_splits(list(reversed(pool)))  # grading order must not matter

    ids = lambda rs: [r["threehop_idx"] for r in rs]  # noqa: E731
    checks = {
        "test N == 150": len(a_test) == TEST_N,
        "selection N == 50": len(a_sel) == SELECTION_N,
        "test/selection disjoint": not (set(ids(a_test)) & set(ids(a_sel))),
        "deterministic across calls": ids(a_test) == ids(b_test) and ids(a_sel) == ids(b_sel),
        "independent of pool order": ids(a_test) == ids(b_test),
        "no overlap with Stage-1 110": not (set(ids(a_test) + ids(a_sel)) & stage1_consumed()),
        "all ids >= frame start": min(ids(a_test) + ids(a_sel)) >= START_IDX,
    }
    # the draw order is load-bearing: selection-first would give a different test split
    sel_first = random.Random(SELECTION_SEED).sample(sorted(pool, key=lambda r: r["threehop_idx"]),
                                                     SELECTION_N)
    checks["draw order matters (selection-first differs)"] = (
        set(ids(sel_first)) != set(ids(a_sel)))

    print("=== split-draw selftest ($0, synthetic pool of 351) ===")
    for k, v in checks.items():
        print(f"  {'PASS' if v else 'FAIL'}  {k}")
    ok = all(checks.values())
    print(f"\n  {'ALL PASS' if ok else 'FAILURES PRESENT'}")
    print(f"  test[:5]={ids(a_test)[:5]}  selection[:5]={ids(a_sel)[:5]}")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true", help="$0 determinism/disjointness check")
    ap.add_argument("--splits-only", action="store_true",
                    help="re-draw both splits from an existing test_pool_graded.jsonl ($0)")
    ap.add_argument("--force", action="store_true",
                    help="re-grade and OVERWRITE splits that are already committed. Almost never "
                         "right: see the guard below.")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    # IDEMPOTENCE GUARD. APPROVED-testsplit stays on disk after the spend as the record of it, so
    # the gate alone no longer stops a second run -- this does. A re-grade would re-spend ~$3.23 and
    # then OVERWRITE both splits via commit_split(). The draws are seeded and the frame is fixed, so
    # they would PROBABLY come back identical -- but grading is an LM call, and temp-0 re-execution
    # is measurably not byte-stable here (2026-08-03: 15/24 rendered feedback blocks reproduced
    # across three same-venv re-runs). If any one of the 700 claims graded differently, the
    # imperfect pool shifts, both splits move, and every sha256 already recorded downstream --
    # starting with the smoke's endpoints.json -- silently stops matching.
    if os.path.exists(OUT_MANIFEST) and not args.force and not args.dry_run:
        man = json.load(open(OUT_MANIFEST))
        print("REFUSING: both splits are already committed.")
        for k in ("test", "selection"):
            print(f"  {k:9} n={man[k]['n']:>3}  seed={man[k]['seed']}  sha256={man[k]['sha256']}")
        print(f"\n{os.path.basename(OUT_MANIFEST)} exists, so this would re-grade the 700-claim "
              f"frame (~$3.23) and overwrite both splits.")
        print("  --splits-only  re-draw from the existing graded pool ($0, no re-grade)")
        print("  --dry-run      print the plan and spend nothing")
        print("  --force        re-grade and overwrite anyway (invalidates downstream sha256s)")
        return 1

    consumed = stage1_consumed()
    est = N_GRADE * USD_PER_CLAIM

    print("=== §8a test split + §8b selection split (one grading pass) ===")
    print(f"  Stage-1 consumed         : {len(consumed)} threehop_idx (disjoint by construction)")
    print("  already-graded remainder : 13 imperfect, all recall=0.0  -> N<100, STOP fired")
    print(f"  fixed frame              : threehop_idx {START_IDX}..{START_IDX + N_GRADE - 1} "
          f"({N_GRADE} claims, no early stop)")
    print(f"  expected imperfect       : ~{int(N_GRADE * IMPERFECT_RATE)} at rate {IMPERFECT_RATE:.3f}")
    print(f"  test split               : N={TEST_N}, random.Random({TEST_SEED})   [drawn FIRST]")
    print(f"  selection split          : N={SELECTION_N}, random.Random({SELECTION_SEED})   "
          f"[drawn from the remainder]")
    print(f"  estimated spend          : ~${est:.2f}   (cap ${SPEND_CAP:.2f})")

    if args.dry_run:
        print("\n[dry-run] no gate check, no grading, no spend. Nothing written.")
        return 0

    if args.splits_only:
        if not os.path.exists(OUT_POOL):
            print(f"missing {OUT_POOL}: nothing to draw from")
            return 1
        print("\n[splits-only] $0 — redrawing from the existing graded pool")
        records = [json.loads(line) for line in open(OUT_POOL, "rb")]
    else:
        gate = require("APPROVED-testsplit")
        print(f"[gate] proceeding under {gate['gate']}\n")
        records = grade_frame()

    imperfect = [r for r in records if r["recall"] < 1.0]
    print(f"\n  imperfect pool: {len(imperfect)} / {len(records)} graded")
    test, selection = draw_splits(imperfect)

    print("\n=== committed splits (sha256 recorded BEFORE any evaluation exists) ===")
    prov = {
        "test": commit_split(OUT_TEST, "test", TEST_SEED, test, len(imperfect), consumed),
        "selection": commit_split(OUT_SELECTION, "selection", SELECTION_SEED, selection,
                                  len(imperfect), consumed),
    }
    t_ids = {r["threehop_idx"] for r in test}
    s_ids = {r["threehop_idx"] for r in selection}
    assert not (t_ids & s_ids), "test and selection splits overlap — STOP"
    print(f"\n  disjoint: test ∩ selection = ∅ ✓   both ∩ Stage-1 consumed = ∅ ✓")
    print(f"  next: backfill_stage1.py --run (APPROVED-backfill), then the live runs")
    json.dump(prov, open(os.path.join(HERE, "splits_manifest.json"), "w"), indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
