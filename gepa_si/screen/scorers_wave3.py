"""Wave 3 — output-parsing-gated scorers (parent Generated Outputs).

11. output-pathology / structural repairability — built here. The hypothesis: a SUBSTANTIVE,
    STRUCTURED, COMPLETE parent output that still failed constraints is a locally-repairable
    format miss (high value to re-expose); an empty/short/truncated output is global
    noncompliance (low value). Purely OUTPUT-derived (length / structure / completeness), so it
    is orthogonal to constraint-identity and difficulty — NOT a verifier-margin re-run (those
    margins stay parked, PROJECT_STATE 7).

12. batch coherent-gap + diverse-inputs (b=3) — NOT built. Its premise (a shared #8 coverage-gap
    direction across the 3 examples) rests on coverage_gap, which screened as difficulty-
    contaminated/weak; and batch-level correlation is ceilinged by 335/351 singleton signatures.
    Recorded as built-but-deprioritized.
"""

from __future__ import annotations

import re

import numpy as np
import pandas as pd

from gepa_si.screen.corpus_io import RunData, _load, load_corpus

WAVE3_COLS = ["output_repairability", "output_n_words"]

_BULLET = re.compile(r"(?m)^\s*([-*•]|\d+[.)])\s+")
_HEADER = re.compile(r"(?m)^\s*(#{1,6}\s+|\*\*.+\*\*\s*$)")
_COMPLETE_END = re.compile(r"[.!?\"'`)\]}]\s*$")


def extract_parent_outputs(run: RunData) -> dict[int, list[str]]:
    """{iteration: [parent Generated Output per example_pos]} from reflective_dataset_built."""
    out: dict[int, list[str]] = {}
    for rec in _load(run.log_path):
        if rec.get("event") != "reflective_dataset_built":
            continue
        comps = rec.get("components") or list((rec.get("dataset") or {}).keys())
        if not comps:
            continue
        ds = (rec.get("dataset") or {}).get(comps[0]) or []
        out[rec["iteration"]] = [str(e.get("Generated Outputs") or "") for e in ds]
    return out


def _features(text: str) -> tuple[float, float]:
    """(repairability composite in [0,1], n_words)."""
    n_words = float(len(text.split()))
    if n_words == 0:
        return 0.0, 0.0
    has_structure = bool(_BULLET.search(text) or _HEADER.search(text) or "\n\n" in text)
    complete = bool(_COMPLETE_END.search(text))
    substantive = min(1.0, n_words / 120.0)
    repairability = substantive * (0.5 + 0.5 * has_structure) * (0.5 + 0.5 * complete)
    return float(repairability), n_words


def build_wave3_matrix(runs: list[RunData] | None = None) -> pd.DataFrame:
    if runs is None:
        runs = load_corpus()
    rows = []
    for run in runs:
        outs = extract_parent_outputs(run)
        for c in run.cycles:
            texts = outs.get(c.iteration, [])
            for p in range(len(c.failed_ids_per_example)):
                txt = texts[p] if p < len(texts) else ""
                rep, nw = _features(txt)
                rows.append({
                    "seed": run.seed, "b": run.b, "iteration": c.iteration, "example_pos": p,
                    "output_repairability": rep,
                    "output_n_words": np.log1p(nw),   # log-scaled; rank-based screen anyway
                })
    return pd.DataFrame(rows)
