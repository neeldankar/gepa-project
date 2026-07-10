"""§13-4 micro-smoke: three-arm counter audit with a MOCKED task LM. $0, no API calls.

Review R10: "A T-only smoke cannot detect the most damaging bug class." Threat 8 is asymmetric
budget counting -- if arm B counts differently from T/C on the moved code, a T-only smoke passes
and the arms launch silently unmatched. So all three arms run here, through the SAME GEPAEngine
wiring, and every counter increment is checked against the §6a five-site model:

    site 1  state.py:661                 seed valset eval        +|D_pareto|   once
    site 2  reflective_mutation.py:164   parent minibatch        +len(drawn)   per event   (3 B / 6 T,C)
    site 3  reflective_mutation.py:332   child minibatch         +3            per event
    site 4  engine.py:137                accept valset eval      +|D_pareto|   per accept
    site 5  merge.py:392                 merge                   NEVER (merge_proposer=None)

Predicted:  total = |D_pareto| + (parent+child)*events + |D_pareto|*accepts

The mock adapter replaces the LM entirely: scores are a deterministic function of (example id,
candidate text). Arm T still runs the REAL novelty scorer against the REAL pinned embedding model,
so the in-loop novelty path is exercised for free.

Also quantifies v2 §20 open decision 1 by running T and C under BOTH skip_perfect_scope settings.

Run:  analysis/state_dep/.venv-armT/bin/python analysis/state_dep/count_audit.py
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from gepa.core.adapter import EvaluationBatch  # noqa: E402
from gepa.core.engine import GEPAEngine  # noqa: E402
from gepa.core.state import EvaluationCache  # noqa: E402,F401  (imported to document that we do NOT use it)
from gepa.logging.experiment_tracker import create_experiment_tracker  # noqa: E402
from gepa.proposer.reflective_mutation.reflective_mutation import ReflectiveMutationProposer  # noqa: E402
from gepa.strategies.candidate_selector import ParetoCandidateSelector  # noqa: E402
from gepa.strategies.component_selector import RoundRobinReflectionComponentSelector  # noqa: E402
from gepa.strategies.eval_policy import FullEvaluationPolicy  # noqa: E402
from gepa.utils.stop_condition import MaxMetricCallsStopper  # noqa: E402

from proposer import SubsetSelectingProposer  # noqa: E402
from sampler import LoggingEpochShuffledBatchSampler  # noqa: E402

N_TRAIN = 100
N_VAL = 10
MAX_METRIC_CALLS = 300
COMP = "gen_query.predict"
SEED_CANDIDATE = {COMP: "seed instruction"}
SCORE_LATTICE = (0.0, 1 / 3, 2 / 3, 1.0)


# ----------------------------------------------------------------- mock adapter (no LM, no API)
def _det_score(example_id, candidate_text: str) -> float:
    h = hashlib.sha256(f"{example_id}|{candidate_text}".encode()).digest()
    return SCORE_LATTICE[h[0] % 4]


class MockAdapter:
    """Deterministic stand-in for DspyAdapter. Never calls an LM.

    Records every evaluate() call so the audit can decompose the counter by call category without
    monkeypatching gepa. Each evaluated example is exactly one metric call, so

        total_num_evals  ==  sum of len(batch) over all evaluate() calls

    is the strongest available invariant, and it holds only if nothing is silently cached.
    """

    def __init__(self):
        self.calls: list[tuple[int, bool]] = []  # (n_examples, capture_traces)

    @property
    def n_examples_evaluated(self) -> int:
        return sum(n for n, _ in self.calls)

    @property
    def parent_examples(self) -> int:
        return sum(n for n, ct in self.calls if ct)

    @property
    def parent_calls(self) -> int:
        return sum(1 for _, ct in self.calls if ct)

    def child_and_valset(self, n_val: int) -> tuple[int, int, int]:
        """Non-trace calls split by batch size: valset calls are exactly n_val wide."""
        child = sum(n for n, ct in self.calls if not ct and n != n_val)
        valset = sum(n for n, ct in self.calls if not ct and n == n_val)
        valset_calls = sum(1 for n, ct in self.calls if not ct and n == n_val)
        return child, valset, valset_calls

    def evaluate(self, batch, candidate, capture_traces=False):
        self.calls.append((len(batch), bool(capture_traces)))
        text = candidate[COMP]
        scores = [_det_score(ex["id"], text) for ex in batch]
        outputs = [{"id": ex["id"]} for ex in batch]
        trajectories = None
        if capture_traces:
            trajectories = [{"id": ex["id"], "score": s} for ex, s in zip(batch, scores)]
        return EvaluationBatch(outputs=outputs, scores=scores, trajectories=trajectories, objective_scores=None)

    def make_reflective_dataset(self, candidate, eval_batch, components_to_update):
        """One item per trajectory, 1:1 with the batch. Feedback mimics HoVer's rigid template."""
        items = []
        for t in eval_batch.trajectories or []:
            eid, s = t["id"], t["score"]
            n_ok = int(round(s * 3))
            got = [f"Doc{eid}_{k}" for k in range(n_ok)]
            missed = [f"Doc{eid}_{k}" for k in range(n_ok, 3)]
            items.append(
                {
                    "Inputs": f"claim {eid}",
                    "Generated Outputs": f"query for {eid}",
                    "Feedback": (
                        f"Correctly retrieved {n_ok}/3 gold documents: {got}. "
                        f"Documents remaining to be retrieved: {missed}."
                    ),
                }
            )
        return {c: items for c in components_to_update}


class _MockTexts:
    """Replaces the reflection LM call. Mixed in ahead of the proposer in the MRO."""

    def propose_new_texts(self, curr_prog, reflective_dataset, components_to_update):
        n = len(reflective_dataset[components_to_update[0]])
        blob = "".join(x["Feedback"] for x in reflective_dataset[components_to_update[0]])
        tag = hashlib.sha256(blob.encode()).hexdigest()[:8]
        return {c: f"{curr_prog[c]}|rev{tag}({n})" for c in components_to_update}


class MockBaseProposer(_MockTexts, ReflectiveMutationProposer):
    pass


class MockSubsetProposer(_MockTexts, SubsetSelectingProposer):
    pass


def build_engine(arm: str, seed: int, skip_perfect_scope: str, embedder, run_dir=None):
    trainset = [{"id": i} for i in range(N_TRAIN)]
    valset = [{"id": 1000 + i} for i in range(N_VAL)]

    adapter = MockAdapter()
    rng = random.Random(seed)  # gepa's SHARED stream (sampler + pareto selector)
    minibatch_size = 3 if arm == "B" else 6
    batch_sampler = LoggingEpochShuffledBatchSampler(minibatch_size=minibatch_size, rng=rng)
    tracker = create_experiment_tracker(
        use_wandb=False, wandb_api_key=None, wandb_init_kwargs=None,
        use_mlflow=False, mlflow_tracking_uri=None, mlflow_experiment_name=None,
    )

    class _Silent:
        def log(self, *a, **k):
            pass

    logger = _Silent()
    common = dict(
        logger=logger,
        trainset=trainset,
        adapter=adapter,
        candidate_selector=ParetoCandidateSelector(rng=rng),
        module_selector=RoundRobinReflectionComponentSelector(),
        batch_sampler=batch_sampler,
        perfect_score=1.0,
        skip_perfect_score=True,
        experiment_tracker=tracker,
        reflection_lm=None,
        callbacks=None,
    )
    if arm == "B":
        proposer = MockBaseProposer(**common)
    else:
        proposer = MockSubsetProposer(
            arm=arm, seed=seed, skip_perfect_scope=skip_perfect_scope, embedder=embedder, **common
        )

    engine = GEPAEngine(
        adapter=adapter,
        run_dir=run_dir,
        valset=valset,
        seed_candidate=dict(SEED_CANDIDATE),
        perfect_score=1.0,
        seed=seed,
        reflective_proposer=proposer,
        merge_proposer=None,  # site 5 unreachable (v2 §6a)
        frontier_type="instance",
        logger=logger,
        experiment_tracker=tracker,
        callbacks=None,
        stop_callback=MaxMetricCallsStopper(max_metric_calls=MAX_METRIC_CALLS),
        val_evaluation_policy=FullEvaluationPolicy(),
        # Stage 1 ran with NO evaluation cache: gepa.optimize defaults cache_evaluation=False
        # (api.py:80) => evaluation_cache=None. With a cache on, a child example already seen by the
        # parent returns actual_evals_count < 3 and the counter silently under-counts. Match Stage 1.
        evaluation_cache=None,
        raise_on_exception=True,
    )
    return engine, proposer, adapter, batch_sampler, tracker


def run_arm(arm: str, seed: int, skip_perfect_scope: str, embedder):
    engine, proposer, adapter, sampler, tracker = build_engine(arm, seed, skip_perfect_scope, embedder)
    with tracker:
        state = engine.run()

    events = getattr(proposer, "event_log", None)
    child_bearing = [t for t in state.full_program_trace if t.get("new_subsample_scores") is not None]
    accepts = sum(1 for t in state.full_program_trace if "new_program_idx" in t)
    n_cand = len(state.program_candidates)

    parent_per_event = 3 if arm == "B" else 6
    child_ex, valset_ex, valset_calls = adapter.child_and_valset(N_VAL)

    # Skipped events: the parent rolled out (and was counted) but no child was ever proposed --
    # skip_perfect_score, or no trajectories. They burn `parent_per_event` calls each.
    skipped = adapter.parent_calls - len(child_bearing)

    # The five-site model (v2 §6a), reconstructed from what the adapter was actually asked to do:
    #   seed valset (10, once) + accept valsets (10 each) + parent minibatches + child minibatches
    predicted = (
        N_VAL                                        # site 1, seed valset
        + parent_per_event * adapter.parent_calls    # site 2, parent minibatch (incl. skipped events)
        + 3 * len(child_bearing)                     # site 3, child minibatch, chosen 3 only
        + N_VAL * accepts                            # site 4, accept-triggered valset
    )                                                # site 5 (merge) is unreachable

    # The strong invariant: every example handed to the adapter is exactly one metric call.
    counter_eq_examples = state.total_num_evals == adapter.n_examples_evaluated

    # leakage checks
    bad_batch = [len(t["subsample_ids"]) for t in child_bearing if len(t["subsample_ids"]) != 3]
    drew6 = [t for t in child_bearing if len(t.get("statedep_drawn_ids", [])) == 6]

    return {
        "arm": arm,
        "seed": seed,
        "skip_perfect_scope": skip_perfect_scope if arm != "B" else "n/a",
        "child_bearing_events": len(child_bearing),
        "skipped_events": skipped,
        "accepts": accepts,
        "candidates_incl_seed": n_cand,
        "accepts_eq_ncand_minus_1": accepts == n_cand - 1,
        "total_num_evals": state.total_num_evals,
        "predicted_total": predicted,
        "counter_matches_model": state.total_num_evals == predicted,
        "adapter_examples_evaluated": adapter.n_examples_evaluated,
        "counter_eq_examples": counter_eq_examples,
        "parent_evals_per_event": parent_per_event,
        "parent_examples": adapter.parent_examples,
        "child_examples": child_ex,
        "valset_examples": valset_ex,
        "valset_calls": valset_calls,
        "valset_calls_eq_1_plus_accepts": valset_calls == 1 + accepts,
        "child_ex_eq_3_per_event": child_ex == 3 * len(child_bearing),
        "parent_ex_eq_M_per_call": adapter.parent_examples == parent_per_event * adapter.parent_calls,
        "trace_batch_sizes_all_3": not bad_batch,
        "events_drawing_6": len(drew6),
        "epoch_reshuffles": sum(1 for d in sampler.draws if d["reshuffled_this_call"]),
        "first_reshuffle_iteration": next(
            (d["iteration"] for d in sampler.draws if d["reshuffled_this_call"] and d["iteration"] > 0), None
        ),
        "archive_size_final": len(getattr(proposer, "archive_texts", [])),
        "event_log": events,
    }


def main() -> int:
    from novelty import load_embedder

    print("=== loading pinned embedder (local, $0) ===")
    embedder = load_embedder()

    rows = []
    print("\n=== running three arms, mocked task LM, MAX_METRIC_CALLS=300, seed=0 ===")
    rows.append(run_arm("B", 0, "n/a", None))
    for scope in ("all6", "chosen3"):
        rows.append(run_arm("C", 0, scope, embedder))
        rows.append(run_arm("T", 0, scope, embedder))

    print("\n" + "=" * 118)
    print("COUNTER DECOMPOSITION vs the §6a five-site model")
    print("=" * 118)
    print(f"{'arm':<4} {'skip_scope':<10} {'ev':>4} {'skip':>5} {'acc':>4} "
          f"{'parent':>7} {'child':>6} {'valset':>7} {'counter':>8} {'predict':>8} {'match':>6} {'ctr=ex':>7} {'b==3':>6}")
    print("-" * 118)
    ok = True
    for r in rows:
        good = (
            r["counter_matches_model"]
            and r["counter_eq_examples"]
            and r["trace_batch_sizes_all_3"]
            and r["accepts_eq_ncand_minus_1"]
            and r["valset_calls_eq_1_plus_accepts"]
            and r["child_ex_eq_3_per_event"]
            and r["parent_ex_eq_M_per_call"]
        )
        ok &= good
        print(f"{r['arm']:<4} {r['skip_perfect_scope']:<10} {r['child_bearing_events']:>4} {r['skipped_events']:>5} "
              f"{r['accepts']:>4} {r['parent_examples']:>7} {r['child_examples']:>6} {r['valset_examples']:>7} "
              f"{r['total_num_evals']:>8} {r['predicted_total']:>8} {str(r['counter_matches_model']):>6} "
              f"{str(r['counter_eq_examples']):>7} {str(r['trace_batch_sizes_all_3']):>6}")
    print("=" * 118)
    print("  parent = site 2 (len(drawn): 3 in B, 6 in T/C, incl. skipped events)")
    print("  child  = site 3 (chosen 3 only)   valset = site 1 + site 4 (10 x (1 + accepts))")
    print("  merge (site 5) never fired: merge_proposer=None")

    print("\n=== per-arm invariants ===")
    for r in rows:
        print(f"  {r['arm']}/{r['skip_perfect_scope']:<8} "
              f"valset_calls==1+accepts: {r['valset_calls_eq_1_plus_accepts']}  "
              f"child==3/event: {r['child_ex_eq_3_per_event']}  "
              f"parent=={r['parent_evals_per_event']}/call: {r['parent_ex_eq_M_per_call']}  "
              f"accepts==ncand-1: {r['accepts_eq_ncand_minus_1']}  "
              f"drew6: {r['events_drawing_6']}")

    print("\n=== epoch-boundary check (v2 §7a: b=3 reshuffles at i=34; b=6 at i=17) ===")
    for r in rows:
        print(f"  arm {r['arm']:<2} scope={r['skip_perfect_scope']:<8} reshuffles={r['epoch_reshuffles']} "
              f"first_reshuffle_at_i={r['first_reshuffle_iteration']}")

    print("\n=== §20 open decision 1: skip_perfect_score asymmetry (measured) ===")
    for arm in ("C", "T"):
        a6 = next(r for r in rows if r["arm"] == arm and r["skip_perfect_scope"] == "all6")
        a3 = next(r for r in rows if r["arm"] == arm and r["skip_perfect_scope"] == "chosen3")
        print(f"  arm {arm}: events all6={a6['child_bearing_events']}  chosen3={a3['child_bearing_events']}  "
              f"(delta {a3['child_bearing_events'] - a6['child_bearing_events']})")
    b = rows[0]
    print(f"  arm B (b=3, scope moot): events={b['child_bearing_events']}")

    out = os.path.join(HERE, "count_audit_result.json")
    with open(out, "w") as fh:
        json.dump([{k: v for k, v in r.items() if k != "event_log"} for r in rows], fh, indent=2)
    print(f"\nwrote {out}")

    print("\nAUDIT PASS" if ok else "\nAUDIT FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
