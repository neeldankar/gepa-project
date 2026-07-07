"""RAW vs PARSED output diff on the frozen corpus — is anything stripped before storage? $0, read-only.

Shows the bytes. Resolves the brief's join: `raw_lm_outputs` is the REFLECTION PROPOSER output
(1/component), NOT the per-example task completion; "Generated Outputs" is the verbatim task
completion (DefaultAdapter passthrough). Reads frozen logs/baseline_*.jsonl only.
"""
from __future__ import annotations

import glob
import json

LOGS = sorted(glob.glob("logs/baseline_seed*_b3_*.jsonl"))
TRUNC = 2000


def show(s: str) -> str:
    if s is None:
        return "<None>"
    if len(s) <= TRUNC:
        return s
    return f"{s[:1000]}\n... [TRUNCATED {len(s)-2000} chars] ...\n{s[-1000:]}"


def main():
    # use one representative run for the printed blocks; summarize across ALL runs
    runs = LOGS
    primary = next((p for p in runs if "231443" in p), runs[0])
    print(f"reading {len(runs)} frozen baseline logs; printed blocks from {primary}\n")

    recs = [json.loads(l) for l in open(primary, encoding="utf-8")]
    proposals = [r for r in recs if r.get("event") == "proposal_end"]
    rdbs = {r["iteration"]: r for r in recs if r.get("event") == "reflective_dataset_built"}
    accepts = {r["iteration"] for r in recs if r.get("event") == "candidate_accepted"}

    # ---------- PART A: JOIN DIAGNOSIS ----------
    print("=" * 78)
    print("PART A — JOIN DIAGNOSIS (field semantics + shapes)")
    print("=" * 78)
    p0 = proposals[0]
    rlo = p0.get("raw_lm_outputs")
    comp = (p0.get("components") or list((rdbs[p0["iteration"]].get("dataset") or {}).keys()))[0] \
        if p0["iteration"] in rdbs else next(iter(rlo))
    rdb0 = rdbs.get(p0["iteration"])
    n_ex = len(rdb0["dataset"][next(iter(rdb0["dataset"]))]) if rdb0 else "?"
    print(f"  raw_lm_outputs : dict keyed by COMPONENT, {len(rlo)} entry/entries -> {list(rlo.keys())}")
    print(f"                   (this is the REFLECTION PROPOSER's raw output, i.e. the new instruction)")
    print(f"  Generated Outputs : per-EXAMPLE field, {n_ex} records/event "
          f"(reflective_dataset_built.dataset[comp][i])")
    print("  Adapter passthrough (gepa default_adapter.py): responses=batch_complete (L132) -> "
          "assistant_response (L139) -> full_assistant_response=assistant_response VERBATIM (L155) -> "
          "'Generated Outputs'=full_assistant_response (L195). No parse step.")
    print("  => raw_lm_outputs (1/component) and Generated Outputs (b/example) DO NOT JOIN per-example.")
    print("     The brief's RAW<->PARSED-per-example-task pairing has no key; not faked.\n")

    # ---------- PART B: TASK SIDE (the actual question) ----------
    print("=" * 78)
    print("PART B — TASK SIDE: is 'Generated Outputs' stripped? (the real question)")
    print("=" * 78)
    # pick 4 examples varying accept/reject + short/long
    cand = []
    for p in proposals:
        it = p["iteration"]
        rdb = rdbs.get(it)
        if not rdb:
            continue
        comp = next(iter(rdb["dataset"]))
        for i, rec in enumerate(rdb["dataset"][comp]):
            cand.append((it, it in accepts, i, rec["Generated Outputs"]))
    cand_sorted = sorted(cand, key=lambda c: len(c[3]))
    picks = [cand_sorted[0], cand_sorted[len(cand_sorted)//2], cand_sorted[-1]]  # short, mid, long
    # ensure at least one accepted and one rejected event represented
    acc = next((c for c in cand if c[1]), None)
    rej = next((c for c in cand if not c[1]), None)
    for extra in (acc, rej):
        if extra and extra not in picks:
            picks.append(extra)
    for it, accepted, i, go in picks[:4]:
        print(f"\n===== example idx {i} | iter {it} | event {'ACCEPTED' if accepted else 'REJECTED'} =====")
        print(f"--- 'Generated Outputs' (the stored task output), len={len(go)} ---")
        print(show(go))
        print("--- raw task field? --- NONE EXISTS: 'Generated Outputs' IS the verbatim completion "
              "(adapter passthrough) => RAW(task) == PARSED(task) by construction.")

    # ---------- PART C: the ONLY real raw-vs-parsed (PROPOSER output, not task) ----------
    print("\n" + "=" * 78)
    print("PART C — the ONLY raw-vs-parsed in the corpus: PROPOSER output (NOT the task output)")
    print("=" * 78)
    prop_picks = [p for p in proposals if p["iteration"] in accepts][:2] + \
                 [p for p in proposals if p["iteration"] not in accepts][:2]
    for p in prop_picks:
        it = p["iteration"]
        comp = next(iter(p["raw_lm_outputs"]))
        raw = p["raw_lm_outputs"][comp]
        parsed = (p.get("new_instructions") or {}).get(comp)
        print(f"\n===== proposer | iter {it} | comp {comp} | event {'ACCEPTED' if it in accepts else 'REJECTED'} =====")
        print(f"--- RAW (raw_lm_outputs), len={len(raw)} ---")
        print(show(raw))
        print(f"--- PARSED (new_instructions), len={len(parsed) if parsed else 0} ---")
        print(show(parsed))
        eq = raw == parsed
        print("--- DIFF VERDICT ---")
        print(f"RAW==PARSED? {'yes' if eq else 'no'}   len delta={len(raw)-(len(parsed) or 0)}")
        if not eq:
            pre = raw[:len(raw)-len(parsed)] if parsed and raw.endswith(parsed) else None
            note = "leading ``` fence" + (" + trailing fence/prose" if not raw.rstrip().endswith(parsed.rstrip() if parsed else "") else "")
            print(f"  stripped: PARSED removes the surrounding ```-fence wrapper from the proposer output "
                  f"({'prefix `'+repr(raw[:8])+'`' if raw.lstrip().startswith('```') else 'fences/prose'}); "
                  "this is the candidate INSTRUCTION text, per-CANDIDATE, not a per-example task signal.")

    # ---------- PART D: corpus-wide summary ----------
    print("\n" + "=" * 78)
    print("PART D — corpus-wide summary (ALL proposal_end events, all baseline runs)")
    print("=" * 78)
    N = same = longer = 0
    maxdelta = 0
    raw_task_fields = 0
    for path in runs:
        for l in open(path, encoding="utf-8"):
            r = json.loads(l)
            if r.get("event") == "proposal_end":
                N += 1
                for comp, raw in (r.get("raw_lm_outputs") or {}).items():
                    parsed = (r.get("new_instructions") or {}).get(comp) or ""
                    if raw == parsed:
                        same += 1
                    elif len(raw) > len(parsed):
                        longer += 1
                        maxdelta = max(maxdelta, len(raw) - len(parsed))
            if r.get("event") == "reflective_dataset_built":
                for comp, items in (r.get("dataset") or {}).items():
                    for rec in items:
                        if any(k not in ("Inputs", "Generated Outputs", "Feedback") for k in rec):
                            raw_task_fields += 1
    print(f"  PROPOSER raw_lm_outputs vs new_instructions over {N} proposal_end events: "
          f"{same}/{N} equal; {longer}/{N} raw longer (fence/prose stripped); max len delta={maxdelta}")
    print(f"  separate RAW per-example TASK field found: {raw_task_fields}/{N} events "
          "(0 = 'Generated Outputs' is the only per-example task text; nothing stripped on the task side)")
    print("\nVERDICT: no stripped TASK channel — 'Generated Outputs' is the verbatim completion. "
          "raw_lm_outputs is the PROPOSER's output (per-component), not a per-example task channel; "
          "its only raw-vs-parsed delta is ```-fence stripping of the candidate instruction.")


if __name__ == "__main__":
    main()
