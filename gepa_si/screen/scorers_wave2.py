"""Wave 2 — reconstruction-gated scorers (parent system-prompt text).

8.  coverage-gap (3-way, here ABSENT/PRESENT) — LEAD; residualize on ITERATION.
9.  seed-to-parent regression — lost capability (constraints the seed passed, parent now fails).
10. coverage-gap x valset-prevalence interaction — uncovered AND transferable.

Parent prompts reconstructed via scorer_inputs.reconstruct_prompts (verified complete on all
10 runs). Scorer #9's seed baseline is SPARSE by construction (the seed's per-constraint results
exist only where candidate 0 was the parent) — coverage is reported, not assumed dense.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gepa_si.screen.corpus_io import RunData, load_corpus
from gepa_si.screen import scorer_inputs as si

WAVE2_COLS = ["coverage_gap", "coverage_gap_x_prevalence", "seed_to_parent_regression"]

ABSENT_W = 1.0       # proposer can ADD a generalizing rule — highest value
PRESENT_W = 0.25     # rule present but ignored — lower value


def _seed_pass_map(run: RunData) -> dict[tuple[int, str], float]:
    """{(trainset_idx, cid): seed pass(1)/fail(0)} from cycles where candidate 0 was the parent."""
    out: dict[tuple[int, str], float] = {}
    for c in run.cycles:
        if c.parent_id != 0:
            continue
        for p, obj in enumerate(c.parent_objscores):
            j = c.minibatch_ids[p]
            for k, v in obj.items():
                out[(j, si._strip(k))] = float(v)
    return out


def build_wave2_matrix(runs: list[RunData] | None = None) -> tuple[pd.DataFrame, dict]:
    """Per-event Wave-2 scorer columns + a coverage-diagnostics dict (sparsity of #9)."""
    if runs is None:
        runs = load_corpus()
    prevalence = si.valset_meta()["prevalence"]
    rows = []
    n_events = 0
    n_seed_covered = 0          # events with >=1 failed constraint the seed had evaluated
    n_absent_total = 0
    n_failed_total = 0
    for run in runs:
        prompts = si.reconstruct_prompts(run.log_path)
        seed_pass = _seed_pass_map(run)
        for c in run.cycles:
            prompt_lower = (prompts.get(c.parent_id) or "").lower()
            for p, failed in enumerate(c.failed_ids_per_example):
                j = c.minibatch_ids[p]
                cov_gap = 0.0
                cov_x_prev = 0.0
                lost = 0.0
                covered_here = False
                for cid in failed:
                    cls = si.classify_coverage(prompt_lower, cid)
                    absent = cls == "ABSENT"
                    cov_gap += ABSENT_W if absent else PRESENT_W
                    if absent:
                        cov_x_prev += prevalence.get(si._strip(cid), 0.0)
                        n_absent_total += 1
                    # seed-to-parent: seed passed cid on this example, parent now fails it
                    sp = seed_pass.get((j, si._strip(cid)))
                    if sp is not None:
                        covered_here = True
                        if sp == 1.0:
                            lost += 1.0
                    n_failed_total += 1
                rows.append({
                    "seed": run.seed, "b": run.b, "iteration": c.iteration, "example_pos": p,
                    "coverage_gap": cov_gap,
                    "coverage_gap_x_prevalence": cov_x_prev,
                    "seed_to_parent_regression": lost,
                })
                n_events += 1
                n_seed_covered += int(covered_here)
    diag = {
        "n_events": n_events,
        "seed_coverage_frac": n_seed_covered / n_events if n_events else 0.0,
        "absent_frac_of_failed": n_absent_total / n_failed_total if n_failed_total else 0.0,
    }
    return pd.DataFrame(rows), diag
