"""Coverage_gap matcher hand-audit: dump distinct (parent-prompt, failed-type) pairs + verdict.

The matcher unit of correctness is (evolved system prompt, constraint TYPE) -> ABSENT/PRESENT.
Sample distinct pairs spanning types; print the prompt + type + matcher label so a human can
judge precision/recall. Offline, $0, read-only.
"""

from __future__ import annotations

import numpy as np

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.scorer_inputs import (
    classify_coverage, constraint_type, reconstruct_prompts, _compiled_cues, _strip,
)


def main():
    runs = [r for r in load_corpus() if r.b == 3]
    # collect distinct (seed, parent_id, type) with an example failed constraint
    seen = {}
    for run in runs:
        prompts = reconstruct_prompts(run.log_path)
        for c in run.cycles:
            for failed in c.failed_ids_per_example:
                for cid in failed:
                    t = constraint_type(cid)
                    key = (run.seed, c.parent_id, t)
                    if key not in seen:
                        seen[key] = {"seed": run.seed, "parent_id": c.parent_id, "type": t,
                                     "cid": _strip(cid), "prompt": prompts.get(c.parent_id, "")}
    pairs = list(seen.values())
    # sample ~15 spanning distinct types
    rng = np.random.default_rng(1)
    by_type = {}
    for p in pairs:
        by_type.setdefault(p["type"], []).append(p)
    sample = []
    for t, lst in sorted(by_type.items()):
        sample.append(lst[rng.integers(len(lst))])
    rng.shuffle(sample)
    sample = sample[:16]

    print(f"distinct (prompt,type) pairs in corpus: {len(pairs)} across {len(by_type)} types")
    print(f"hand-audit sample: {len(sample)} pairs spanning types\n")
    for i, p in enumerate(sample):
        label = classify_coverage(p["prompt"].lower(), p["cid"])
        cues = _compiled_cues().get(p["type"], [])
        hit = [c for c in cues if c in p["prompt"].lower()]
        print(f"===== [{i}] type={p['type']}  example_cid={p['cid']}  -> MATCHER={label}")
        print(f"  cues for type: {cues}")
        print(f"  cues HIT in prompt: {hit}")
        print(f"  --- parent prompt (seed{p['seed']} cand{p['parent_id']}) ---")
        print("  " + p["prompt"][:1600].replace("\n", "\n  "))
        print()


if __name__ == "__main__":
    main()
