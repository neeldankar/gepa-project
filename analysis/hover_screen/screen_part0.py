"""HoVer heterogeneity screen — Part 0 (0.2, 0.3, 0.4, 0.6). $0, read-only on frozen dirs.

Covers:
  0.2 reflection-object coverage on all 243 SAME-arm objects (3 sections per example block)
  0.3 dump 10 verbatim SAME-arm objects -> analysis/hover_screen/si_sample.md
  0.4 join verification: pair dirs <-> child-bearing trace entries <-> reflection events, b check
  0.6 revisit coverage within-run

0.5 (checksum recompute) lives in screen_part05_outcomes.py — run under scratch/hover_probe/.venv
to reproduce the exact RNG streams of the committed results.md.

Run from repo root:  analysis/hover_screen/.venv-screen/bin/python analysis/hover_screen/screen_part0.py
"""
from __future__ import annotations

import json
import os
import re
import statistics

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PAIRS = os.path.join(REPO, "analysis", "ablation", "hover_swap", "pairs")
STAGE1 = os.path.join(REPO, "scratch", "hover_stage1")
OUTDIR = os.path.join(REPO, "analysis", "hover_screen")
SEEDS = list(range(8))
EXPECTED_PER_SEED = {0: 32, 1: 34, 2: 28, 3: 33, 4: 27, 5: 34, 6: 28, 7: 27}
CHILDLESS = {2: [5, 15], 6: [27]}

anomalies: list[str] = []


def note(msg):
    anomalies.append(msg)
    print(f"ANOMALY: {msg}")


# ---------------------------------------------------------------- stage-1 load
def load_stage1(seed):
    d = json.load(open(os.path.join(STAGE1, f"stage1_seed{seed}", "gepa_result.json")))
    refl = json.load(open(os.path.join(STAGE1, f"stage1_seed{seed}", "reflections.json")))
    trace = d["full_program_trace"]
    childbearing = [t for t in trace if t.get("new_subsample_scores") is not None]
    childless = [t["i"] for t in trace if t.get("new_subsample_scores") is None]
    return d, refl, trace, childbearing, childless


# ---------------------------------------------------------------- SI parsing
EX_SPLIT = re.compile(r"^# Example (\d+)$", re.MULTILINE)
SEC_SPLIT = re.compile(r"^## (Inputs|Generated Outputs|Feedback)$", re.MULTILINE)


def parse_si(text, where):
    """Split a rendered reflection prompt into example blocks, each with its 3 sections.

    Returns list of dicts {n, Inputs, Generated Outputs, Feedback} (missing section -> absent key).
    """
    parts = EX_SPLIT.split(text)
    # parts = [preamble, num1, block1, num2, block2, ...]
    if len(parts) < 3:
        note(f"{where}: no '# Example N' blocks found")
        return []
    blocks = []
    for k in range(1, len(parts) - 1, 2):
        n, body = int(parts[k]), parts[k + 1]
        if k + 2 >= len(parts):  # last block: cut at the closing fence line
            m = re.search(r"^```\s*$", body, re.MULTILINE)
            if m:
                body = body[: m.start()]
            else:
                note(f"{where}: example {n}: closing fence not found in last block")
        secs = SEC_SPLIT.split(body)
        blk = {"n": n}
        for j in range(1, len(secs) - 1, 2):
            name, content = secs[j], secs[j + 1]
            if name in blk:
                note(f"{where}: example {n}: duplicate section '{name}'")
            blk[name] = content.strip("\n")
        blocks.append(blk)
    return blocks


# ================================================================ 0.4 join
def part04():
    print("\n===== 0.4 JOIN VERIFICATION =====")
    pair_dirs = sorted(os.listdir(PAIRS))
    pair_keys = set()
    metas = {}
    for pid in pair_dirs:
        m = re.fullmatch(r"seed(\d+)_i(\d+)", pid)
        if not m:
            note(f"pair dir '{pid}' does not match seed<S>_i<T>")
            continue
        s, t = int(m.group(1)), int(m.group(2))
        pair_keys.add((s, t))
        metas[(s, t)] = json.load(open(os.path.join(PAIRS, pid, "meta.json")))
    print(f"pair dirs: {len(pair_dirs)}  parsed keys: {len(pair_keys)}")
    if len(pair_keys) != 243:
        note(f"expected 243 unique (seed,trace_i) pair keys, got {len(pair_keys)}")

    events = {}  # (seed, trace_i) -> event record
    b_values = set()
    per_seed_ok = True
    for seed in SEEDS:
        d, refl, trace, cb, cl = load_stage1(seed)
        if cl != CHILDLESS.get(seed, []):
            note(f"seed{seed}: child-less trace indices {cl} != documented {CHILDLESS.get(seed, [])}")
        n_ev = len(refl)
        if len(cb) != n_ev:
            note(f"seed{seed}: {len(cb)} child-bearing trace entries != {n_ev} reflection events")
        if n_ev != EXPECTED_PER_SEED[seed]:
            note(f"seed{seed}: {n_ev} reflection events != expected {EXPECTED_PER_SEED[seed]}")
            per_seed_ok = False
        if [r["idx"] for r in refl] != list(range(1, n_ev + 1)):
            note(f"seed{seed}: reflections.json idx not 1..{n_ev}")
        rs = json.load(open(os.path.join(STAGE1, f"stage1_seed{seed}", "run_summary.json")))
        seed_keys = set()
        n_accept = 0
        for ordinal, t in enumerate(cb):
            key = (seed, t["i"])
            b_values.add(len(t["subsample_ids"]))
            accept = sum(t["new_subsample_scores"]) > sum(t["subsample_scores"])
            n_accept += int(accept)
            events[key] = dict(seed=seed, trace_i=t["i"], ordinal=ordinal, idx=ordinal + 1,
                               subsample_ids=t["subsample_ids"], accept=accept,
                               parent_cand=t["selected_program_candidate"],
                               subsample_scores=t["subsample_scores"],
                               new_subsample_scores=t["new_subsample_scores"])
            seed_keys.add(key)
        if n_accept != rs["accepts_inferred"]:
            note(f"seed{seed}: recomputed accepts {n_accept} != run_summary accepts_inferred {rs['accepts_inferred']}")
        if rs["candidates_incl_seed"] != n_accept + 1:
            note(f"seed{seed}: candidates_incl_seed {rs['candidates_incl_seed']} != accepts+1 {n_accept+1}")
        got_pairs = {k for k in pair_keys if k[0] == seed}
        if got_pairs != seed_keys:
            note(f"seed{seed}: pair keys != child-bearing trace keys; "
                 f"pairs-only={sorted(got_pairs - seed_keys)}, trace-only={sorted(seed_keys - got_pairs)}")

    # one-to-one and meta consistency
    n_meta_ok = n_pos_ok = n_ord_ok = 0
    for key, ev in sorted(events.items()):
        mt = metas.get(key)
        if mt is None:
            continue
        if mt["event_ordinal"] == ev["ordinal"]:
            n_ord_ok += 1
        else:
            note(f"{key}: meta event_ordinal {mt['event_ordinal']} != child-bearing ordinal {ev['ordinal']}")
        if mt["A_e_pos"] == ev["subsample_ids"]:
            n_pos_ok += 1
        else:
            note(f"{key}: meta A_e_pos {mt['A_e_pos']} != trace subsample_ids {ev['subsample_ids']}")
        if mt["parent_candidate_idx"] == ev["parent_cand"]:
            n_meta_ok += 1
        else:
            note(f"{key}: meta parent_candidate_idx {mt['parent_candidate_idx']} != trace {ev['parent_cand']}")
    print(f"one-to-one: {len(events)} events, {len(metas)} metas; "
          f"event_ordinal ok {n_ord_ok}/243, A_e_pos==subsample_ids ok {n_pos_ok}/243, "
          f"parent_candidate ok {n_meta_ok}/243")

    # b from config + data
    cfg = open(os.path.join(STAGE1, "stage1_run.py")).read()
    m = re.search(r"reflection_minibatch_size\s*=\s*(\d+)", cfg)
    b_cfg = int(m.group(1)) if m else None
    print(f"b: config reflection_minibatch_size={b_cfg}; observed batch sizes in trace={sorted(b_values)}")
    if b_cfg != 3 or b_values != {3}:
        note(f"minibatch size: config={b_cfg}, observed={sorted(b_values)} (expected 3)")

    # trainset manifest byte-identical across seeds
    blobs = {seed: open(os.path.join(STAGE1, f"stage1_seed{seed}", "trainset_manifest.json"), "rb").read()
             for seed in SEEDS}
    ident = len({b for b in blobs.values()}) == 1
    print(f"trainset_manifest.json byte-identical across 8 seeds: {ident}")
    if not ident:
        note("trainset_manifest.json differs across seeds")
    return events, metas


# ================================================================ 0.2 coverage
def part02():
    print("\n===== 0.2 REFLECTION-OBJECT COVERAGE (SAME arm, 243 events) =====")
    sizes = {"Inputs": [], "Generated Outputs": [], "Feedback": []}
    n_full = n_partial = n_missing = 0
    per_event_blocks = {}
    for pid in sorted(os.listdir(PAIRS)):
        f = os.path.join(PAIRS, pid, "reflect_in_SAME.txt")
        if not os.path.exists(f):
            note(f"{pid}: reflect_in_SAME.txt missing")
            n_missing += 1
            continue
        text = open(f, encoding="utf-8").read()
        blocks = parse_si(text, f"{pid}/reflect_in_SAME.txt")
        per_event_blocks[pid] = blocks
        if len(blocks) != 3:
            note(f"{pid}: {len(blocks)} example blocks, expected 3")
        ok = True
        for blk in blocks:
            for sec in sizes:
                if sec in blk:
                    sizes[sec].append(len(blk[sec].encode("utf-8")))
                else:
                    ok = False
                    note(f"{pid}: example {blk['n']}: section '{sec}' absent")
        if ok and len(blocks) == 3:
            n_full += 1
        elif blocks:
            n_partial += 1
        else:
            n_missing += 1
    print(f"events with all 3 sections x 3 examples: {n_full} / partial: {n_partial} / missing-or-unparsed: {n_missing}")
    for sec, v in sizes.items():
        print(f"  {sec:18} n={len(v):4}  bytes min/median/max = "
              f"{min(v)}/{int(statistics.median(v))}/{max(v)}")
    return per_event_blocks


# ================================================================ 0.3 sample
def part03(events):
    print("\n===== 0.3 SI SAMPLE DUMP =====")
    rng = np.random.default_rng(20260709)
    acc = sorted([k for k, e in events.items() if e["accept"]])
    rej = sorted([k for k, e in events.items() if not e["accept"]])
    pick_a = [acc[i] for i in rng.choice(len(acc), 5, replace=False)]
    pick_r = [rej[i] for i in rng.choice(len(rej), 5, replace=False)]
    picks = sorted(pick_a + pick_r)
    seeds_covered = {k[0] for k in picks}
    print(f"picked {len(picks)} events, seeds covered: {sorted(seeds_covered)} "
          f"(accepted {len(pick_a)}, rejected {len(pick_r)})")
    if len(seeds_covered) < 4:
        note(f"si_sample covers only {len(seeds_covered)} seeds (<4) — reselect needed")
    out = [
        "# si_sample.md — 10 verbatim SAME-arm reflection objects",
        "",
        "Selection: rng=default_rng(20260709); 5 accepted + 5 rejected events drawn without",
        "replacement from the sorted (seed, trace_i) lists. Verbatim file contents follow.",
        "",
    ]
    for k in picks:
        pid = f"seed{k[0]}_i{k[1]}"
        text = open(os.path.join(PAIRS, pid, "reflect_in_SAME.txt"), encoding="utf-8").read()
        ev = events[k]
        out.append(f"\n---\n\n## {pid}  (ordinal={ev['ordinal']}, accept={ev['accept']})\n")
        out.append("~~~~~~~~text")
        out.append(text)
        out.append("~~~~~~~~")
    with open(os.path.join(OUTDIR, "si_sample.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"[wrote {os.path.join(OUTDIR, 'si_sample.md')}]")
    return picks


# ================================================================ 0.6 revisit
def part06(events):
    print("\n===== 0.6 REVISIT COVERAGE (within-run) =====")
    from collections import Counter
    total_ge2 = 0
    total_events_revisit = 0
    dist_all = Counter()
    for seed in SEEDS:
        evs = sorted([e for k, e in events.items() if e["seed"] == seed], key=lambda e: e["ordinal"])
        visits = Counter()
        n_ev_revisit = 0
        for e in evs:
            if any(visits[x] >= 1 for x in e["subsample_ids"]):
                n_ev_revisit += 1
            for x in e["subsample_ids"]:
                visits[x] += 1
        ge2 = sum(1 for c in visits.values() if c >= 2)
        dist = Counter(visits.values())
        dist_all.update(visits.values())
        total_ge2 += ge2
        total_events_revisit += n_ev_revisit
        print(f"  seed{seed}: examples visited={len(visits)}, >=2 visits={ge2}, "
              f"events w/ >=1 revisited example={n_ev_revisit}/{len(evs)}, "
              f"visit-count dist={dict(sorted(dist.items()))}")
    print(f"  TOTAL: examples with >=2 visits (summed over runs)={total_ge2}; "
          f"events with >=1 revisited example={total_events_revisit}/243; "
          f"pooled visit-count dist={dict(sorted(dist_all.items()))}")


def main():
    events, metas = part04()
    part02()
    part03(events)
    part06(events)
    print("\n===== ANOMALY LIST =====")
    if anomalies:
        for a in anomalies:
            print(f"  - {a}")
    else:
        print("  none")
    json.dump({f"{k[0]}_{k[1]}": {kk: vv for kk, vv in e.items()}
               for k, e in sorted(events.items())},
              open(os.path.join(OUTDIR, "events_index.json"), "w"), indent=0, default=bool)
    print(f"[wrote {os.path.join(OUTDIR, 'events_index.json')}]")


if __name__ == "__main__":
    main()
