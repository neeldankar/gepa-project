"""Instruction-following constraint evaluator for gepa's DefaultAdapter.

`IFConstraintEvaluator` implements gepa's `Evaluator` protocol
(`__call__(self, data, response) -> EvaluationResult`) and is passed via
`optimize(evaluator=...)`. gepa forwards it into `DefaultAdapter(model=task_lm,
evaluator=...)`, so the SIEventLogger wiring is unchanged. The structured `feedback`
string this returns becomes the per-example "Feedback" SI in `on_reflective_dataset_built`.

It mirrors the canonical per-constraint check sequence from
`../IFBench/evaluation_lib.py::test_instruction_following_strict` exactly. The check
interface is identical between the two verifier registries we support:

  - "ifbench"  -> IFBench's INSTRUCTION_DICT (OOD/"unseen" test constraints)
  - "ifevalg"  -> open-instruct IFEvalG's INSTRUCTION_DICT (IF-RLVR "seen" train constraints)

Each example selects its registry via `data["registry"]` (default "ifbench"). This lets
the faithful generalization protocol (train on IFEvalG-verified, test on IFBench OOD) use
one evaluator across different constraint sets / verifier registries.

Both source repos are pristine sibling clones (never modified, never installed as
packages); we add them to sys.path at import time. IFBench imports top-level, IFEvalG
imports package-qualified, so the two coexist under distinct sys.modules keys.
"""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# IFBench: pristine sibling clone, imported top-level.
_IFBENCH_DIR = os.path.abspath(os.path.join(_REPO_ROOT, "..", "IFBench"))
if _IFBENCH_DIR not in sys.path:
    sys.path.insert(0, _IFBENCH_DIR)

# open-instruct (IFEvalG): pristine sibling sparse clone, imported package-qualified.
_OPEN_INSTRUCT_DIR = os.path.abspath(os.path.join(_REPO_ROOT, "..", "open-instruct"))
if _OPEN_INSTRUCT_DIR not in sys.path:
    sys.path.insert(0, _OPEN_INSTRUCT_DIR)

import instructions_registry as _ifbench_registry  # noqa: E402  (top-level, IFBench)

from gepa.adapters.default_adapter.default_adapter import EvaluationResult  # noqa: E402

IFBENCH_DICT = _ifbench_registry.INSTRUCTION_DICT

# IFEvalG: prefer the sibling sparse clone; fall back to a vendored copy if absent.
try:
    from open_instruct.IFEvalG.instructions_registry import (  # noqa: E402
        INSTRUCTION_DICT as IFEVALG_DICT,
    )

    IFEVALG_SOURCE = "sparse-clone (../open-instruct)"
except Exception:  # pragma: no cover - fallback path
    _VENDOR_DIR = os.path.join(_REPO_ROOT, "vendor")
    if _VENDOR_DIR not in sys.path:
        sys.path.insert(0, _VENDOR_DIR)
    from open_instruct.IFEvalG.instructions_registry import (  # noqa: E402
        INSTRUCTION_DICT as IFEVALG_DICT,
    )

    IFEVALG_SOURCE = "vendored (vendor/open_instruct/IFEvalG)"

# Registry selector keyed by each example's data["registry"].
_REGISTRIES = {
    "ifbench": IFBENCH_DICT,
    "ifevalg": IFEVALG_DICT,
}

# Backwards-compatible alias for the IFBench-only entry point.
INSTRUCTION_DICT = IFBENCH_DICT


class IFConstraintEvaluator:
    """Scores a response against an example's instruction-following constraints.

    Registry per example via `data.get("registry", "ifbench")` in {"ifbench","ifevalg"}.

    score = fraction of constraints satisfied (mean of per-constraint booleans).
    NOTE: the paper's headline metric is prompt-level strict (all-or-nothing). The
    fraction gives a richer gradient for SI generation and nearly coincides here
    because most examples are single-constraint.
    """

    def __call__(self, data, response: str) -> EvaluationResult:
        prompt = data["input"]
        registry = _REGISTRIES[data.get("registry", "ifbench")]
        instruction_ids = data.get("instruction_id_list") or []
        kwargs_list = data.get("kwargs") or []

        results: list[tuple[str, str, bool]] = []  # (constraint_id, description, followed)
        for index, instruction_id in enumerate(instruction_ids):
            try:
                cls = registry[instruction_id]
                inst = cls(instruction_id)
                # A kwargs entry may be None (no args) or a dict with None values.
                raw_kw = kwargs_list[index] if index < len(kwargs_list) else None
                kw = {k: v for k, v in (raw_kw or {}).items() if v is not None}
                description = inst.build_description(**kw)
                args = inst.get_instruction_args()
                if args and "prompt" in args:
                    # Some checkers need the original prompt; canonical re-builds here.
                    inst.build_description(prompt=prompt)
                followed = bool(response and response.strip() and inst.check_following(response))
            except Exception as e:  # surface, don't swallow (guardrail)
                raise RuntimeError(
                    f"{data.get('registry', 'ifbench')} checker '{instruction_id}' "
                    f"(index {index}) raised: {e!r}"
                ) from e
            results.append((instruction_id, description, followed))

        n = len(results)
        n_ok = sum(1 for _, _, ok in results if ok)
        score = (n_ok / n) if n else 1.0

        # -- structured feedback == the SI ----------------------------------
        lines = [f"Satisfied {n_ok}/{n} constraints."]
        for cid, description, ok in results:
            mark = "✓" if ok else "✗"
            status = "satisfied" if ok else "FAILED"
            lines.append(f"{mark} [{cid}] {status} — {description}")
        feedback = "\n".join(lines)

        # -- objective_scores: ALWAYS a dict (never None; batch rule requires
        #    all-not-None). Disambiguate duplicate ids within one example.
        objective_scores: dict[str, float] = {}
        for index, (cid, _desc, ok) in enumerate(results):
            key = cid if cid not in objective_scores else f"{cid}#{index}"
            objective_scores[key] = 1.0 if ok else 0.0

        return EvaluationResult(score=score, feedback=feedback, objective_scores=objective_scores)


# Backwards-compatible alias: step-3's IFBench script imports IFBenchEvaluator.
IFBenchEvaluator = IFConstraintEvaluator
