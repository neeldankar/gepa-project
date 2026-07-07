"""Read-only extractor: the FULL per-example reflection object (the real scoring unit).

Every prior scorer/probe read only the per-example **Feedback** string. Direct byte-capture
(analysis/reflection_capture/REPORT.md) proved the reflection LM actually receives, per
example, a TRIPLE: ``## Inputs`` (task prompt) + ``## Generated Outputs`` (parent completion,
verbatim) + ``## Feedback`` (per-constraint checklist). All three already sit in the frozen
corpus at ``reflective_dataset_built.dataset[component][example]`` — no re-log needed.

This module exposes that triple per (run, iteration, example_pos) and a verification gate that
each field is a verbatim substring of the SAME event's ``proposal_end.prompts.system_prompt``
(the object proven 3-way byte-identical to the reflection LM input). $0, pure log reading.
"""

from __future__ import annotations

from dataclasses import dataclass

from gepa_si.screen.corpus_io import RunData, _load


@dataclass
class Triple:
    inputs: str
    outputs: str
    feedback: str

    def full(self) -> str:
        """The full per-example object text the proposer reads (Inputs+Outputs+Feedback)."""
        return f"{self.inputs}\n\n{self.outputs}\n\n{self.feedback}"

    def output_on_input(self) -> str:
        """Output conditioned on input (drops the id-determined Feedback channel)."""
        return f"{self.inputs}\n\n{self.outputs}"


def extract_reflection_triples(run: RunData) -> dict[int, list[Triple]]:
    """{iteration: [Triple per example_pos]} from each reflective_dataset_built event.

    Mirrors scorers_wave3.extract_parent_outputs but keeps all three fields. The first
    component's dataset is used (single-component program: 'system_prompt').
    """
    out: dict[int, list[Triple]] = {}
    for rec in _load(run.log_path):
        if rec.get("event") != "reflective_dataset_built":
            continue
        comps = rec.get("components") or list((rec.get("dataset") or {}).keys())
        if not comps:
            continue
        ds = (rec.get("dataset") or {}).get(comps[0]) or []
        out[rec["iteration"]] = [
            Triple(
                inputs=str(e.get("Inputs") or ""),
                outputs=str(e.get("Generated Outputs") or ""),
                feedback=str(e.get("Feedback") or ""),
            )
            for e in ds
        ]
    return out


def _system_prompts(run: RunData) -> dict[int, str]:
    """{iteration: proposal_end.prompts.system_prompt} — the byte-exact reflection object."""
    out: dict[int, str] = {}
    for rec in _load(run.log_path):
        if rec.get("event") != "proposal_end":
            continue
        sp = (rec.get("prompts") or {}).get("system_prompt")
        if sp is not None and rec.get("iteration") is not None:
            out[rec["iteration"]] = str(sp)
    return out


def verify_substring_containment(run: RunData) -> dict:
    """Assert every triple field is a verbatim substring of its event's system_prompt.

    Returns {checked, ok, failures:[...]}. A pass proves the assembled triple IS what the
    proposer saw (not a reconstruction). Events without a paired proposal_end are skipped
    (rare 1-eval anomaly) and counted under `skipped`.
    """
    triples = extract_reflection_triples(run)
    sps = _system_prompts(run)
    checked = ok = skipped = 0
    failures: list[dict] = []
    for it, tl in triples.items():
        sp = sps.get(it)
        if sp is None:
            skipped += 1
            continue
        for p, t in enumerate(tl):
            checked += 1
            # Compare on stripped fields: GEPA's prompt template trims a trailing space
            # off each rendered field, so the raw stored value differs by <=1 whitespace
            # char while the content is byte-identical (verified: only trailing ws differs).
            miss = [
                name
                for name, val in (("Inputs", t.inputs), ("Generated Outputs", t.outputs),
                                  ("Feedback", t.feedback))
                if val.strip() and val.strip() not in sp
            ]
            if miss:
                failures.append({"iteration": it, "example_pos": p, "missing_fields": miss})
            else:
                ok += 1
    return {"seed": run.seed, "b": run.b, "checked": checked, "ok": ok,
            "skipped": skipped, "failures": failures}
