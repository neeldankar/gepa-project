"""HoVer heterogeneity screen — BM25 rank table + 2.2 fixability feasibility probe. $0, local.

Builds bm25_ranks.csv: for each of the 110 unique examples (100 shared trainset + 10 valset),
the 1-based rank of EACH of its gold titles in the BM25 retrieval for the claim as query,
searched to depth K_CAP=1000; not found within K_CAP -> rank = -1 (censored). Feeds scorer 6
(retrieval hardness) and scorer 15 (fixability); missed titles are a subset of gold titles,
so the same table covers both.

2.2: for a 20-event sample (rng=default_rng(20260710) over the sorted 243 event keys),
report the rank of every SAME-arm missed gold title under its claim. Validates scorer 15.

Retrieval path fidelity: probe.py's own tokenizer/stemmer/search stack, loaded MEMORY-MAPPED
via the hover_swap_run.py monkeypatch pattern (probe.py is frozen and is not modified;
assert_mmap-equivalent check runs before any query).

Run from repo root: scratch/hover_probe/.venv/bin/python analysis/hover_screen/screen_bm25.py
"""
from __future__ import annotations

import csv
import json
import os
import re
import sys
import time

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HOVER_PROBE = os.path.join(REPO, "scratch", "hover_probe")
STAGE1 = os.path.join(REPO, "scratch", "hover_stage1")
OUTDIR = os.path.join(REPO, "analysis", "hover_screen")
K_CAP = 1000

sys.path.insert(0, HOVER_PROBE)
os.chdir(HOVER_PROBE)  # probe.py loads 'bm25s_index' and 'threehop.jsonl' relative to cwd
import bm25s  # noqa: E402
import probe  # noqa: E402  (frozen; not modified — loader is rebound below)


# --- memory-mapped BM25 index: monkeypatch pattern from hover_swap_run.py:24-47 ---
def _load_index_mmap():
    if probe._retriever is None:
        r = bm25s.BM25.load("bm25s_index", load_corpus=True, mmap=True)
        probe._retriever = r
        probe._corpus = r.corpus
    return probe._retriever


probe.load_index = _load_index_mmap


def assert_mmap():
    probe.load_index()
    if not isinstance(probe._retriever.scores["data"], np.memmap):
        raise RuntimeError("BM25 score arrays are not memmapped — mmap patch did not take")
    if type(probe._corpus).__name__ != "JsonlCorpus":
        raise RuntimeError(f"corpus is {type(probe._corpus).__name__}, expected JsonlCorpus (mmap)")


def title_ranks(claim, titles):
    """1-based rank of each title in the depth-K_CAP retrieval for the claim; -1 if beyond."""
    hits = probe.search(claim, k=K_CAP)
    ret = [probe.title_of(h) for h in hits]
    first = {}
    for i, t in enumerate(ret):
        if t not in first:
            first[t] = i + 1
    return {t: first.get(t, -1) for t in titles}


def main():
    assert_mmap()
    print("mmap OK — building rank table")
    manifest = json.load(open(os.path.join(STAGE1, "stage1_seed0", "trainset_manifest.json")))
    graded = {r["threehop_idx"]: r for r in
              (json.loads(l) for l in open(os.path.join(STAGE1, "graded_records.jsonl")))}

    rows = []
    t0 = time.time()
    todo = ([("train", i, tid) for i, tid in enumerate(manifest["train_threehop_ids"])] +
            [("val", i, tid) for i, tid in enumerate(manifest["val_threehop_ids"])])
    for n, (split, pos, tid) in enumerate(todo):
        rec = graded[tid]
        for title, rank in title_ranks(rec["claim"], rec["gold"]).items():
            rows.append(dict(split=split, pos=pos, threehop_idx=tid, title=title, rank=rank))
        if (n + 1) % 20 == 0:
            print(f"  {n+1}/{len(todo)} examples  ({time.time()-t0:.0f}s)")
    with open(os.path.join(OUTDIR, "bm25_ranks.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["split", "pos", "threehop_idx", "title", "rank"])
        w.writeheader()
        w.writerows(rows)
    ranks = [r["rank"] for r in rows]
    cens = sum(1 for r in ranks if r < 0)
    found = sorted(r for r in ranks if r > 0)
    print(f"[wrote bm25_ranks.csv] {len(rows)} title rows; censored(> {K_CAP})={cens}; "
          f"found ranks min/median/max = {found[0]}/{found[len(found)//2]}/{found[-1]}")

    # ---------------- 2.2 fixability probe: 20-event sample ----------------
    print("\n===== 2.2 FIXABILITY FEASIBILITY (20-event sample) =====")
    sig = json.load(open(os.path.join(OUTDIR, "probe_2_1_signatures.json")))
    by_pair = {}
    for r in sig["per_example_sigs"]:
        by_pair.setdefault(r["pair"], {})[r["slot"]] = r["sig"]
    ev_index = json.load(open(os.path.join(OUTDIR, "events_index.json")))
    rank_of = {(r["split"], r["pos"], r["title"]): r["rank"] for r in rows}

    keys = sorted(by_pair)
    rng = np.random.default_rng(20260710)
    pick = [keys[i] for i in rng.choice(len(keys), 20, replace=False)]
    train_ids = manifest["train_threehop_ids"]
    n_missed = n_found = 0
    report = []
    for pid in sorted(pick):
        seed, trace_i = map(int, re.fullmatch(r"seed(\d+)_i(\d+)", pid).groups())
        ev = ev_index[f"{seed}_{trace_i}"]
        for slot in range(3):
            pos = ev["subsample_ids"][slot]
            for title in by_pair[pid][slot]:
                rank = rank_of[("train", pos, title)]
                n_missed += 1
                n_found += int(rank > 0)
                report.append(dict(pair=pid, slot=slot, pos=pos, title=title, rank=rank))
                print(f"  {pid} ex{slot+1} pos={pos:3d}  rank={rank:5d}  {title}")
    print(f"\nmissed titles in sample: {n_missed}; retrievable within {K_CAP}: {n_found} "
          f"({n_found/n_missed:.1%})")
    json.dump({"k_cap": K_CAP, "sample": sorted(pick), "rows": report},
              open(os.path.join(OUTDIR, "probe_2_2_fixability.json"), "w"), indent=1)
    print(f"[wrote {os.path.join(OUTDIR, 'probe_2_2_fixability.json')}]")


if __name__ == "__main__":
    main()
