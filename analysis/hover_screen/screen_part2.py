"""HoVer heterogeneity screen — Part 2.1 missed-title-set signature ceiling probe. $0.

Extracts, for all 243 SAME-arm events, the per-example missed-gold-title sets from the
'## Feedback' lines of reflect_in_SAME.txt ("Documents remaining to be retrieved: [...]"),
cross-checks them against the example's gold titles (join byte-verification), and reports
signature recurrence at both grains with the pre-registered kill rule:

  KILL if singleton share > 0.85 at BOTH grains (per-example and per-batch)
  -> scorers 14 (signature_novelty) and 16 (co_failure) are DEAD on this corpus.

Singleton share (primary, instance-weighted, corpus-wide): fraction of instances whose
signature occurs exactly once across the whole corpus. Corpus-wide pooling is GENEROUS to
the scorer family (more chances to recur than the per-run archives the scorers would use),
so a kill at this grain is conservative. Within-run shares reported alongside.

Run: analysis/hover_screen/.venv-screen/bin/python analysis/hover_screen/screen_part2.py
"""
from __future__ import annotations

import ast
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from screen_part0 import parse_si, PAIRS, STAGE1  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTDIR = os.path.join(REPO, "analysis", "hover_screen")

FEEDBACK_RE = re.compile(
    r"Correctly retrieved (\d+)/(\d+) gold documents: (\[.*?\])\. "
    r"Documents remaining to be retrieved: (\[.*?\])\.", re.DOTALL)
CLAIM_RE = re.compile(r"### claim\n(.*?)\n\n###", re.DOTALL)

anomalies = []


def note(m):
    anomalies.append(m)
    print(f"ANOMALY: {m}")


def main():
    # gold/claim lookup: trainset position -> record
    manifest = json.load(open(os.path.join(STAGE1, "stage1_seed0", "trainset_manifest.json")))
    graded = {r["threehop_idx"]: r for r in
              (json.loads(l) for l in open(os.path.join(STAGE1, "graded_records.jsonl")))}
    train_ids = manifest["train_threehop_ids"]
    ev_index = json.load(open(os.path.join(OUTDIR, "events_index.json")))

    per_ex_sigs = []          # (seed, pid, slot, sig) — sig = sorted tuple of missed titles
    per_batch_sigs = []       # (seed, pid, sig) — sorted tuple of the 3 per-example sigs
    n_claim_ok = n_missed_subset_ok = n_slots = 0
    for pid in sorted(os.listdir(PAIRS)):
        seed, trace_i = map(int, re.fullmatch(r"seed(\d+)_i(\d+)", pid).groups())
        ev = ev_index[f"{seed}_{trace_i}"]
        text = open(os.path.join(PAIRS, pid, "reflect_in_SAME.txt"), encoding="utf-8").read()
        blocks = parse_si(text, pid)
        if len(blocks) != 3:
            note(f"{pid}: {len(blocks)} blocks")
            continue
        batch = []
        for slot, blk in enumerate(blocks):
            n_slots += 1
            pos = ev["subsample_ids"][slot]
            rec = graded[train_ids[pos]]
            m = FEEDBACK_RE.search(blk["Feedback"])
            if not m:
                note(f"{pid} ex{slot+1}: feedback line does not match template: {blk['Feedback'][:80]!r}")
                continue
            correct = ast.literal_eval(m.group(3))
            missed = ast.literal_eval(m.group(4))
            gold = set(rec["gold"])
            if set(missed) | set(correct) == gold and not (set(missed) & set(correct)):
                n_missed_subset_ok += 1
            else:
                note(f"{pid} ex{slot+1}: correct∪missed != gold or overlap "
                     f"(missed={missed}, correct={correct}, gold={sorted(gold)})")
            cm = CLAIM_RE.search(blk["Inputs"] + "\n\n###")
            claim_in_si = cm.group(1).strip() if cm else None
            if claim_in_si == rec["claim"].strip():
                n_claim_ok += 1
            else:
                note(f"{pid} ex{slot+1}: SI claim != trainset claim at pos {pos}")
            sig = tuple(sorted(missed))
            per_ex_sigs.append((seed, pid, slot, sig))
            batch.append(sig)
        per_batch_sigs.append((seed, pid, tuple(sorted(batch))))

    print(f"join byte-verification over {n_slots} example-slots: "
          f"claim match {n_claim_ok}/{n_slots}, correct∪missed==gold {n_missed_subset_ok}/{n_slots}")

    def stats(items, label, exclude_empty=False):
        vals = [s for *_, s in items]
        if exclude_empty:
            vals = [s for s in vals if s != ()]
        cnt = collections.Counter(vals)
        n_inst, n_dist = len(vals), len(cnt)
        singleton_inst = sum(c for c in cnt.values() if c == 1) / n_inst if n_inst else float("nan")
        singleton_dist = sum(1 for c in cnt.values() if c == 1) / n_dist if n_dist else float("nan")
        top = cnt.most_common(10)
        print(f"\n-- {label}{' (empty sigs excluded)' if exclude_empty else ''} --")
        print(f"  instances={n_inst} distinct={n_dist} "
              f"singleton_share_instance={singleton_inst:.4f} singleton_share_distinct={singleton_dist:.4f}")
        for sig, c in top:
            print(f"    x{c}: {sig if sig else '()'}")
        return singleton_inst

    print("\n===== 2.1 SIGNATURE PROBE — corpus-wide (generous grain) =====")
    s_ex = stats(per_ex_sigs, "per-example signatures")
    stats(per_ex_sigs, "per-example signatures", exclude_empty=True)
    s_b = stats(per_batch_sigs, "per-batch signatures")

    print("\n===== 2.1 within-run recurrence (the grain scorers 14/16 would use) =====")
    for grain, items in (("per-example", [(s, sig) for s, _, _, sig in
                                          [(a, b, c, d) for a, b, c, d in per_ex_sigs]]),
                         ("per-batch", [(s, sig) for s, _, sig in per_batch_sigs])):
        singles = []
        for seed in range(8):
            vals = [sig for s, sig in items if s == seed]
            cnt = collections.Counter(vals)
            singles.append(sum(c for c in cnt.values() if c == 1) / len(vals))
        print(f"  {grain}: per-run instance singleton shares = "
              f"{[f'{x:.3f}' for x in singles]}  mean={sum(singles)/8:.4f}")

    kill = s_ex > 0.85 and s_b > 0.85
    print(f"\nKILL RULE (corpus-wide instance singleton share > 0.85 at both grains): "
          f"per-example={s_ex:.4f}, per-batch={s_b:.4f} -> {'KILL 14/16' if kill else 'family lives'}")

    print("\n===== ANOMALIES =====")
    for a in anomalies or ["none"]:
        print(f"  - {a}")

    json.dump({"singleton_instance_per_example": s_ex, "singleton_instance_per_batch": s_b,
               "kill_14_16": kill,
               "per_example_sigs": [{"seed": s, "pair": p, "slot": sl, "sig": list(sig)}
                                    for s, p, sl, sig in per_ex_sigs]},
              open(os.path.join(OUTDIR, "probe_2_1_signatures.json"), "w"))
    print(f"[wrote {os.path.join(OUTDIR, 'probe_2_1_signatures.json')}]")


if __name__ == "__main__":
    main()
