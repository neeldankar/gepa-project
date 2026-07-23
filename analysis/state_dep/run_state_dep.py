"""One live state-dependent run: arm B, C or T at one seed. GATED: APPROVED-liverun.

WHY THIS FILE EXISTS RATHER THAN A `dspy.GEPA` CALL (v2.1 §13-3, B3). `dspy.GEPA` cannot inject a
batch sampler -- its `__init__` has no such parameter (the docstring at
`dspy/teleprompt/gepa/gepa.py:284` claims one; it does not exist) and it hard-passes
`reflection_minibatch_size=3`, tripping the assert at `api.py:304`. `gepa.optimize()` exposes
`batch_sampler` but no proposer, and the 6->3 selection must live in the proposer, between the
parent rollout and `make_reflective_dataset`. So all three arms wire `GEPAEngine` directly,
replicating `api.py:256-387`. Running B through `dspy.GEPA` while T/C used `GEPAEngine` would make
V3's counter-parity check meaningless -- the arms would differ in the harness as well as the arm.

WHAT IS PINNED TO STAGE 1 (v2.1 §0, §13-3). Model gpt-4.1-mini, BM25 retrieval, title-recall metric
with `build_si` feedback, `max_metric_calls=300`, `N_TRAIN=100`, `N_VAL=10`, `num_threads=1`,
`candidate_selection_strategy="pareto"`, `component_selector="round_robin"`, `use_merge=False`
(`merge_proposer=None`), `evaluation_cache=None`, `perfect_score=1.0`, temp-0 task LM with
`cache=False`, temp-1.0 reflection LM with capture. The arm changes exactly two things: the
minibatch is 6 instead of 3 (T, C), and a proposer selects 3 of those 6.

ARMS
    B   stock ReflectiveMutationProposer, minibatch 3.       The cost-matched baseline.
    C   SubsetSelectingProposer, draw 6, pick 3 at random.   The cost-matched control.
    T   SubsetSelectingProposer, draw 6, pick top-3 by SI novelty against the run's archive.

`skip_perfect_scope="chosen3"` (v2.1 §20-1, ratified): the skip gate reads the same 3 examples that
become the reflection minibatch, so B and T/C decide "is there anything to learn here?" about the
same object.

    dry ($0, no gate, no LM):  .venv-armT/bin/python run_state_dep.py --arm T --seed 0 --dry
    live (gated):              .venv-armT/bin/python run_state_dep.py --arm T --seed 0
    live smoke (gated):        .venv-armT/bin/python run_state_dep.py --arm T --seed 0 --smoke

The post-run §8b selection pass is NOT here -- it is `score_candidates.py`, run after the wave.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HOVER_PROBE = os.path.join(REPO, "scratch", "hover_probe")
STAGE1 = os.path.join(REPO, "scratch", "hover_stage1")
RUNS = os.path.join(HERE, "runs")
sys.path.insert(0, HERE)

# ---- pinned to Stage 1; changing any of these voids the run (v2.1 §0) --------------------------
MODEL = "openai/gpt-4.1-mini"
MAX_METRIC_CALLS = 300
N_TRAIN = 100
N_VAL = 10
NUM_THREADS = 1
PERFECT_SCORE = 1.0
SKIP_PERFECT_SCOPE = "chosen3"  # v2.1 §20-1, ratified 2026-07-22
MINIBATCH = {"B": 3, "C": 6, "T": 6}
REFLECT_SIG = "I provided an assistant with the following instructions"
SPEND_CAP = 6.00      # per-run hard tripwire; a Stage-1 run cost $1.91
TRIPWIRE_USD = 5.50   # abort before the cap so the abort itself is not the overspend


def git_commit() -> str:
    try:
        return subprocess.check_output(["git", "-C", REPO, "rev-parse", "HEAD"], text=True).strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def sha256_of(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


# --------------------------------------------------------------------------- data
def stage1_trainset(dspy):
    """Reproduce stage1_run.py:131-141 exactly. Same 110 claims, same order, every arm, every seed.

    Pairing depends on this being identical across arms (v2.1 §7a): the arms must differ in the
    selection rule and nothing else. The split is NOT seed-dependent -- gepa's own rng shuffles it.
    """
    import orjson  # noqa: PLC0415

    recs = [orjson.loads(line) for line in open(os.path.join(STAGE1, "graded_records.jsonl"), "rb")]
    imperfect = [r for r in recs if r["recall"] < 1.0]
    imperfect.sort(key=lambda r: (-r["recall"], r["claim"]))
    need = N_TRAIN + N_VAL
    chosen = imperfect[:need] if len(imperfect) >= need else (imperfect * ((need // len(imperfect)) + 1))[:need]
    examples = [dspy.Example(claim=r["claim"], titles=r["gold"]).with_inputs("claim") for r in chosen]
    ids = [r["threehop_idx"] for r in chosen]
    return examples[:N_TRAIN], examples[N_TRAIN:need], ids[:N_TRAIN], ids[N_TRAIN:need]


# --------------------------------------------------------------------------- the run
def main() -> int:  # noqa: C901
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=("B", "C", "T"))
    ap.add_argument("--seed", required=True, type=int)
    ap.add_argument("--smoke", action="store_true",
                    help="tag the run dir as the excluded live smoke (v2.1 §13-5)")
    ap.add_argument("--dry", action="store_true",
                    help="$0: build the engine, dump the wiring, exit before the first LM call")
    args = ap.parse_args()

    arm, seed = args.arm, args.seed
    name = f"smoke_{arm}_seed{seed}" if args.smoke else f"{arm}_seed{seed}"
    out = os.path.join(RUNS, name)

    # clobber guard (stage1_run.py:33 pattern): never overwrite a completed run
    if not args.dry and os.path.exists(os.path.join(out, "run_summary.json")):
        raise SystemExit(f"REFUSE: {out}/run_summary.json exists — not clobbering {name}")

    # The smoke holds its own gate (v2.1.1 §13-7). It is the measurement the 24-run launch is
    # decided on, so approving it must not be the same act as approving the launch.
    gate_name = "APPROVED-smoke" if args.smoke else "APPROVED-liverun"
    if not args.dry:
        from gates import require
        require(gate_name)

    # ---- imports that need the pinned venv -----------------------------------------------
    sys.path.insert(0, HOVER_PROBE)
    os.chdir(HOVER_PROBE)  # probe resolves bm25s_index/, threehop.jsonl, ../../.env relatively
    import litellm  # noqa: PLC0415
    import probe  # noqa: PLC0415

    import dspy  # noqa: PLC0415
    from dspy.teleprompt.gepa.gepa_utils import DspyAdapter, ScoreWithFeedback  # noqa: PLC0415
    from gepa.core.engine import GEPAEngine  # noqa: PLC0415
    from gepa.core.data_loader import ensure_loader  # noqa: PLC0415
    from gepa.logging.experiment_tracker import create_experiment_tracker  # noqa: PLC0415
    from gepa.proposer.reflective_mutation.reflective_mutation import ReflectiveMutationProposer  # noqa: PLC0415
    from gepa.strategies.candidate_selector import ParetoCandidateSelector  # noqa: PLC0415
    from gepa.strategies.component_selector import RoundRobinReflectionComponentSelector  # noqa: PLC0415
    from gepa.strategies.eval_policy import FullEvaluationPolicy  # noqa: PLC0415
    from gepa.utils.stop_condition import CompositeStopper, FileStopper, MaxMetricCallsStopper  # noqa: PLC0415

    import eval_split as ev  # noqa: PLC0415
    from novelty import MODEL_REVISION, load_embedder, verify_weights_on_disk  # noqa: PLC0415
    from proposer import SubsetSelectingProposer  # noqa: PLC0415
    from sampler import LoggingEpochShuffledBatchSampler  # noqa: PLC0415

    # A dry run writes NOTHING: no run dir, no logs, no reflection capture. Creating the directory
    # early would leave empty run dirs behind that the supervisor's resume logic then has to reason
    # about.
    if not args.dry:
        os.makedirs(out, exist_ok=True)
    probe._load_env()

    # ---- embedder: pinned revision, local only (v2.1 §0) ----------------------------------
    embedder = None
    if arm in ("C", "T"):
        embedder = load_embedder()

    # ---- LMs + capture (stage1_run.py:90-115, verbatim) -----------------------------------
    task_lm = dspy.LM(MODEL, max_tokens=3000, cache=False)
    dspy.configure(lm=task_lm)
    REFLECTIONS: list[dict] = []

    class CaptureDSpyLM(dspy.LM):
        def __call__(self, prompt=None, messages=None, **kwargs):
            is_reflect = isinstance(prompt, str) and prompt.startswith(REFLECT_SIG)
            res = super().__call__(prompt=prompt, messages=messages, **kwargs)
            if is_reflect:
                idx = len(REFLECTIONS) + 1
                raw = res[0] if isinstance(res, list) and res else res
                raw = raw.get("text") if isinstance(raw, dict) else raw
                REFLECTIONS.append({"idx": idx, "prompt": prompt, "output": str(raw)})
                open(f"{out}/reflect_in_{idx}.txt", "w", encoding="utf-8").write(prompt)
                open(f"{out}/reflect_out_{idx}.txt", "w", encoding="utf-8").write(str(raw))
            return res

    reflection_lm = CaptureDSpyLM(MODEL, temperature=1.0, max_tokens=4000, cache=False)

    # ---- spend tripwire on the wire (stage1_run.py:44-64) ---------------------------------
    _cost = {"usd": 0.0}
    _backoffs = {"n": 0}

    def _wire_cb(kwargs, completion_response, start_time, end_time):
        try:
            u = getattr(completion_response, "usage", None) or {}
            pin = u.get("prompt_tokens", 0) if isinstance(u, dict) else getattr(u, "prompt_tokens", 0)
            pout = u.get("completion_tokens", 0) if isinstance(u, dict) else getattr(u, "completion_tokens", 0)
            _cost["usd"] += pin * probe.PRICE_IN + pout * probe.PRICE_OUT
        except Exception:  # noqa: BLE001, S110
            pass
        if _cost["usd"] > TRIPWIRE_USD:
            raise RuntimeError(f"SPEND TRIPWIRE: est ${_cost['usd']:.3f} > ${TRIPWIRE_USD} — aborting")

    def _fail_cb(kwargs, exc, start_time, end_time):
        _backoffs["n"] += 1  # retry/rate-limit counter for the smoke's width decision

    litellm.success_callback = [_wire_cb]
    litellm.failure_callback = [_fail_cb]

    class _NullSink:
        def write(self, _b): pass
        def close(self): pass

    retr_log = _NullSink() if args.dry else open(f"{out}/retrieval_log.jsonl", "wb")
    import orjson  # noqa: PLC0415

    def metric(gold, pred, trace=None, pred_name=None, pred_trace=None):
        g = set(getattr(gold, "titles", []) or [])
        got = set(getattr(pred, "titles", []) or [])
        recall = (len(g & got) / len(g)) if g else 0.0
        fb = probe.build_si(list(g), list(got))
        retr_log.write(orjson.dumps({
            "claim": getattr(gold, "claim", ""), "gold": sorted(g), "retrieved": sorted(got),
            "recall": recall, "n_retrieved": len(got), "overlap": len(g & got),
            "per_hop": getattr(pred, "per_hop", []),
        }) + b"\n")
        return ScoreWithFeedback(score=recall, feedback=fb)

    trainset, valset, train_ids, val_ids = stage1_trainset(dspy)
    student = ev.build_program(dspy, probe)

    # ---- the adapter dspy.GEPA would have built (gepa.py:520-560) --------------------------
    def feedback_fn_creator(pred_name, predictor):
        def feedback_fn(predictor_output, predictor_inputs, module_inputs, module_outputs, captured_trace):
            o = metric(module_inputs, module_outputs, captured_trace, pred_name,
                       [(predictor, predictor_inputs, predictor_output)])
            if hasattr(o, "feedback"):
                if o["feedback"] is None:
                    o["feedback"] = f"This trajectory got a score of {o['score']}."
                return o
            return dict(score=o, feedback=f"This trajectory got a score of {o}.")
        return feedback_fn

    rng = random.Random(seed)  # gepa's SHARED stream: batch sampler + Pareto selector (B5)
    adapter = DspyAdapter(
        student_module=student,
        metric_fn=metric,
        feedback_map={k: feedback_fn_creator(k, v) for k, v in student.named_predictors()},
        failure_score=0.0,
        num_threads=NUM_THREADS,
        add_format_failure_as_feedback=False,
        rng=rng,
        reflection_lm=reflection_lm,
        custom_instruction_proposer=None,
        warn_on_score_mismatch=True,
        reflection_minibatch_size=MINIBATCH[arm],
    )
    seed_candidate = {n: p.signature.instructions for n, p in student.named_predictors()}

    # ---- the engine api.optimize() would have built (api.py:256-387) -----------------------
    log_dir = os.path.join(out, "gepa_log")
    if not args.dry:
        os.makedirs(log_dir, exist_ok=True)  # engine.run() writes here; --dry never gets that far
    tracker = create_experiment_tracker(
        use_wandb=False, wandb_api_key=None, wandb_init_kwargs=None,
        use_mlflow=False, mlflow_tracking_uri=None, mlflow_experiment_name=None,
    )
    batch_sampler = LoggingEpochShuffledBatchSampler(minibatch_size=MINIBATCH[arm], rng=rng)

    class _Logger:
        def log(self, msg):
            print(msg, flush=True)

    logger = _Logger()
    common = dict(
        logger=logger,
        trainset=ensure_loader(trainset),
        adapter=adapter,
        candidate_selector=ParetoCandidateSelector(rng=rng),
        module_selector=RoundRobinReflectionComponentSelector(),
        batch_sampler=batch_sampler,
        perfect_score=PERFECT_SCORE,
        skip_perfect_score=True,
        experiment_tracker=tracker,
        reflection_lm=(lambda x: adapter.stripped_lm_call(x)[0]),
        callbacks=None,
    )
    if arm == "B":
        proposer = ReflectiveMutationProposer(**common)
    else:
        proposer = SubsetSelectingProposer(
            arm=arm, seed=seed, skip_perfect_scope=SKIP_PERFECT_SCOPE, embedder=embedder, **common)

    engine = GEPAEngine(
        adapter=adapter,
        run_dir=log_dir,
        valset=ensure_loader(valset),
        seed_candidate=seed_candidate,
        perfect_score=PERFECT_SCORE,
        seed=seed,
        reflective_proposer=proposer,
        merge_proposer=None,          # site 5 unreachable (v2.1 §6a); gepa.optimize's own default
        frontier_type="instance",
        logger=logger,
        experiment_tracker=tracker,
        callbacks=None,
        stop_callback=CompositeStopper(
            FileStopper(os.path.join(log_dir, "gepa.stop")),
            MaxMetricCallsStopper(MAX_METRIC_CALLS),
        ),                            # exactly what api.py:199-235 composes when run_dir is set
        val_evaluation_policy=FullEvaluationPolicy(),
        evaluation_cache=None,        # Stage 1 ran with no cache; a cache under-counts the budget
        raise_on_exception=True,
        track_best_outputs=False,
        display_progress_bar=True,
    )

    wiring = {
        "run": name, "arm": arm, "seed": seed, "smoke": args.smoke,
        "gate": gate_name,
        "design": "state-dependent-design-v2.1.1-frozen",
        "git_commit": git_commit(),
        "engine": "GEPAEngine (direct wiring, v2.1 §13-3)",
        "minibatch_size": MINIBATCH[arm],
        "proposer": type(proposer).__name__,
        "skip_perfect_scope": SKIP_PERFECT_SCOPE if arm != "B" else "n/a (stock 3-score gate)",
        "skip_perfect_score": True,
        "perfect_score": PERFECT_SCORE,
        "max_metric_calls": MAX_METRIC_CALLS,
        "n_train": len(trainset), "n_val": len(valset),
        "train_threehop_ids": train_ids, "val_threehop_ids": val_ids,
        "num_threads": NUM_THREADS,
        "merge_proposer": None,
        "evaluation_cache": None,
        "candidate_selector": "ParetoCandidateSelector(rng=random.Random(seed))",
        "module_selector": "RoundRobinReflectionComponentSelector",
        "val_evaluation_policy": "FullEvaluationPolicy",
        "stop_callback": f"CompositeStopper(FileStopper, MaxMetricCallsStopper({MAX_METRIC_CALLS}))",
        "task_lm": {"model": MODEL, "max_tokens": 3000, "cache": False, "temperature": "dspy default (0.0)"},
        "reflection_lm": {"model": MODEL, "max_tokens": 4000, "temperature": 1.0, "cache": False},
        "embedding": None if embedder is None else dict(
            revision=MODEL_REVISION, local_files_only=True, **verify_weights_on_disk()),
        "gepa_version": _pkg_version("gepa"),
        "dspy_version": _pkg_version("dspy"),
        "python": sys.version.split()[0],
        "interpreter": sys.executable,
        "spend_cap_usd": SPEND_CAP, "tripwire_usd": TRIPWIRE_USD,
    }

    if args.dry:
        print(json.dumps(wiring, indent=2))
        print("\n[dry] engine built, no gate checked, no LM call made, nothing written.")
        retr_log.close()
        return 0

    json.dump(wiring, open(f"{out}/config.json", "w"), indent=2)
    print(f"=== {name}: arm {arm} seed {seed} mm={MAX_METRIC_CALLS} minibatch={MINIBATCH[arm]} ===",
          flush=True)

    t0 = time.time()
    with tracker:
        state = engine.run()
    wall_s = time.time() - t0
    retr_log.close()

    # ---- persistence (v2.1 §12) ------------------------------------------------------------
    state_dump = {
        "prog_candidate_val_subscores": state.prog_candidate_val_subscores,
        "parent_program_for_candidate": state.parent_program_for_candidate,
        "num_metric_calls_by_discovery": state.num_metric_calls_by_discovery,
        "program_candidates": state.program_candidates,
        "list_of_named_predictors": state.list_of_named_predictors,
        "full_program_trace": state.full_program_trace,
        "n_val": len(valset),
        "trainset_threehop_ids": train_ids,
        "valset_threehop_ids": val_ids,
        "total_num_evals": state.total_num_evals,
    }
    json.dump(state_dump, open(f"{out}/gepa_result.json", "w"), indent=2, ensure_ascii=False,
              default=str)
    json.dump(REFLECTIONS, open(f"{out}/reflections.json", "w"), indent=2, ensure_ascii=False)
    json.dump(getattr(proposer, "event_log", []), open(f"{out}/event_log.json", "w"), indent=2,
              ensure_ascii=False, default=str)
    json.dump(batch_sampler.draws, open(f"{out}/sampler_draws.json", "w"), indent=2, default=str)

    # ---- counter audit against the §6a five-site model, on REAL scores ---------------------
    trace = state.full_program_trace
    child_bearing = [t for t in trace if t.get("new_subsample_scores") is not None]
    accepts = sum(1 for t in trace if "new_program_idx" in t)
    events = len(getattr(proposer, "event_log", [])) or len(child_bearing)
    parent_per_event = MINIBATCH[arm]
    n_parent_calls = len(REFLECTIONS) + (len(trace) - len(child_bearing))
    predicted = (N_VAL + parent_per_event * n_parent_calls + 3 * len(child_bearing) + N_VAL * accepts)

    actual = _spend(task_lm, reflection_lm, probe)
    summary = {
        "run": name, "arm": arm, "seed": seed, "smoke": args.smoke,
        "reflection_events": len(REFLECTIONS),
        "trace_entries": len(trace),
        "child_bearing_events": len(child_bearing),
        "selection_events_logged": events,
        "candidates_incl_seed": len(state.program_candidates),
        "accepts": accepts,
        "total_num_evals": state.total_num_evals,
        "predicted_total_five_site": predicted,
        "counter_matches_model": state.total_num_evals == predicted,
        "task_calls": len(task_lm.history),
        "reflection_calls": len(reflection_lm.history),
        "backoffs": _backoffs["n"],
        "spend_usd": round(actual, 4),
        "wire_est_usd": round(_cost["usd"], 4),
        "wall_clock_s": round(wall_s, 1),
        "peak_rss_mb": _peak_rss_mb(),
        "archive_size_final": len(getattr(proposer, "archive_texts", [])),
        "spend_cap_usd": SPEND_CAP,
    }
    json.dump(summary, open(f"{out}/run_summary.json", "w"), indent=2)

    print("\n===== RUN SUMMARY =====")
    print(json.dumps(summary, indent=2))
    if not summary["counter_matches_model"]:
        print("\nWARNING: budget counter does NOT match the §6a five-site model — flag before analysis.")
    if actual > SPEND_CAP:
        print(f"\nWARNING: spend ${actual:.4f} exceeded cap ${SPEND_CAP}")
    print("\nDONE")
    return 0


def _spend(task_lm, reflection_lm, probe) -> float:
    tot = 0.0
    for lm in (task_lm, reflection_lm):
        for h in list(lm.history):
            u = h.get("usage") or {}
            tot += (u.get("prompt_tokens", 0) * probe.PRICE_IN
                    + u.get("completion_tokens", 0) * probe.PRICE_OUT)
    return tot


def _peak_rss_mb() -> float:
    import resource  # noqa: PLC0415
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1048576.0, 1)  # macOS: bytes


def _pkg_version(name: str) -> str:
    from importlib.metadata import PackageNotFoundError, version  # noqa: PLC0415
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
