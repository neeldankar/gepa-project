"""Stage-2 Phase 0 — census + pairing dry-run ($0, NO API calls).

Read-only on the frozen scratch/hover_stage1/ corpus. Keys on reflection EVENTS (child-bearing
full_program_trace entries == reflections.json entries), never on trace indices. Writes:
  analysis/ablation/hover_swap/census.md        (raw facts only, no interpretation)
  analysis/ablation/hover_swap/pairing_plan.jsonl (243 rows: per-event RNG seed + M=6 draw excl A_e)

  python3 analysis/ablation/hover_swap/make_census.py
"""
from __future__ import annotations
import json, os, random
from collections import Counter

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
S1 = os.path.join(REPO, "scratch", "hover_stage1")
OUT = os.path.join(REPO, "analysis", "ablation", "hover_swap")
os.makedirs(OUT, exist_ok=True)
MANIFEST = {0: 32, 1: 34, 2: 28, 3: 33, 4: 27, 5: 34, 6: 28, 7: 27}
M = 6  # candidate draw breadth per event

def frac_str(x): return {0.0: "0", 1/3: "1/3", 2/3: "2/3", 1.0: "1"}.get(round(x, 3), f"{x:.3f}")

per_seed = {}
allpar = []
tie_batches = 0
multiset_ct = Counter()
integrity = {"out_of_range_ids": 0, "missing_fields": 0, "draw_A_e_collision": 0, "wrong_event_count": 0}
plan_rows = []

for s in range(8):
    d = os.path.join(S1, f"stage1_seed{s}")
    gr = json.load(open(os.path.join(d, "gepa_result.json")))
    tm = json.load(open(os.path.join(d, "trainset_manifest.json")))
    ntrain = tm["n_train"]
    train_ids = tm["train_threehop_ids"]
    events = [e for e in gr["full_program_trace"] if e.get("new_subsample_scores")]
    if len(events) != MANIFEST[s]:
        integrity["wrong_event_count"] += 1
    usable = 0
    for ev in events:
        ss = ev.get("subsample_scores"); ids = ev.get("subsample_ids"); ns = ev.get("new_subsample_scores")
        if ss is None or ids is None or not ns:
            integrity["missing_fields"] += 1; continue
        if any((i < 0 or i >= ntrain) for i in ids):
            integrity["out_of_range_ids"] += 1
        usable += 1
        allpar += list(ss)
        if len(set(ss)) == 1: tie_batches += 1
        multiset_ct[tuple(sorted(round(x, 3) for x in ss))] += 1
        ev_seed = 1_000_000 * s + ev["i"]
        rng = random.Random(ev_seed)
        pool = [i for i in range(ntrain) if i not in set(ids)]
        draw6 = sorted(rng.sample(pool, M))
        if set(draw6) & set(ids): integrity["draw_A_e_collision"] += 1
        plan_rows.append({
            "seed": s, "trace_i": ev["i"],
            "A_e_pos": list(ids),
            "A_e_threehop_ids": [train_ids[i] for i in ids],
            "A_e_parent_scores": list(ss),
            "parent_candidate_idx": ev["selected_program_candidate"],
            "ev_rng_seed": ev_seed,
            "draw6_pos": draw6,
            "draw6_threehop_ids": [train_ids[i] for i in draw6],
        })
    per_seed[s] = usable

total = sum(per_seed.values())
with open(os.path.join(OUT, "pairing_plan.jsonl"), "w") as f:
    for r in plan_rows:
        f.write(json.dumps(r) + "\n")

n = len(allpar)
score_hist = Counter(round(x, 3) for x in allpar)

L = []
L.append("# Stage-2 HoVer batch-swap — Phase 0 census (raw facts, no interpretation)\n")
L.append("- Source: frozen `scratch/hover_stage1/` (8 seeds). Event keying: child-bearing "
         "`full_program_trace` entries (== `reflections.json` == manifest); trace indices NOT used.")
L.append("- Estimand/design ports IFBench batch-swap v2; pairing adapted to HoVer failure-profile match.\n")
L.append("## Usable events per seed (parent scores present + >=1 child)\n")
L.append("| seed | usable events | manifest |")
L.append("|---|---|---|")
for s in range(8):
    L.append(f"| {s} | {per_seed[s]} | {MANIFEST[s]} |")
L.append(f"| **total** | **{total}** | **243** |")
L.append(f"\n- Total usable pairs (one A_e vs B_e per event): **{total}**")
L.append("\n## Integrity (all must be 0)\n")
for k, v in integrity.items():
    L.append(f"- {k}: {v}")
L.append("\n## Pairing plan (dry-run, $0 — no API)\n")
L.append(f"- {len(plan_rows)} rows in `pairing_plan.jsonl`. Per event: RNG seed = `1_000_000*seed + "
         f"trace_i`; M={M} candidate positions drawn without replacement from the 100-claim trainset "
         "excluding A_e's 3 positions.")
L.append("- Each row: `seed, trace_i, A_e_pos, A_e_threehop_ids, A_e_parent_scores, "
         "parent_candidate_idx, ev_rng_seed, draw6_pos, draw6_threehop_ids`.")
L.append("- Matched-batch SELECTION (pick 3 of 6 by parent-score-multiset match) is deferred to "
         "Phase 1 (requires running the parent on the 6 candidates).")
L.append("\n## Tie shares — parent minibatch (A_e) per-example scores\n")
L.append(f"- N = {n} scores ({total} events x 3). Metric grid {{0, 1/3, 2/3, 1}}.")
L.append("")
L.append("| score | count | share |")
L.append("|---|---|---|")
for k in sorted(score_hist):
    L.append(f"| {frac_str(k)} | {score_hist[k]} | {100*score_hist[k]/n:.1f}% |")
L.append(f"\n- share exactly 0: {100*score_hist.get(0.0,0)/n:.1f}%")
L.append(f"- all-3-equal (tied) minibatches: {tie_batches}/{total} ({100*tie_batches/total:.1f}%)")
L.append(f"\n## Parent-score multisets (failure-match feasibility, raw counts)\n")
L.append(f"- {len(multiset_ct)} distinct multisets across {total} events.")
L.append("")
L.append("| multiset | count |")
L.append("|---|---|")
for k, v in multiset_ct.most_common():
    L.append(f"| ({', '.join(frac_str(x) for x in k)}) | {v} |")
open(os.path.join(OUT, "census.md"), "w").write("\n".join(L) + "\n")

print("wrote:", os.path.join(OUT, "census.md"))
print("wrote:", os.path.join(OUT, "pairing_plan.jsonl"), f"({len(plan_rows)} rows)")
print("\n" + "\n".join(L))
