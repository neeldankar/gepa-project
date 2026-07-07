import json, os, tempfile
from gepa.core.callbacks import GEPACallback
from si_event_logger import SIEventLogger

class FakeNpFloat:           # mimics np.float64 (.item() -> python float)
    def __init__(self, v): self.v = v
    def item(self): return self.v
class FakeState:             # mimics GEPAState (NOT json-serializable)
    def __repr__(self): return "<GEPAState>"

d = tempfile.mkdtemp()
path = os.path.join(d, "run_test.jsonl")
log = SIEventLogger(path, run_id="run_test")

# 1) protocol conformance
# gepa duck-types callbacks (getattr per method); partial impls are intended.
for m in ["on_reflective_dataset_built","on_minibatch_sampled","on_valset_evaluated","on_candidate_accepted","on_iteration_end"]:
    assert callable(getattr(log, m, None)), f"missing {m}"

# 2) drive synthetic events shaped like the real TypedDicts
log.on_optimization_start({"trainset_size": 50, "valset_size": 100,
                           "seed_candidate": {"instructions": "seed"}, "config": {"b": 3}})
log.on_candidate_selected({"iteration": 7, "candidate_idx": 2, "score": FakeNpFloat(0.61)})
log.on_minibatch_sampled({"iteration": 7, "minibatch_ids": [12, 4, 88], "trainset_size": 50})
log.on_evaluation_end({"iteration": 7, "candidate_idx": 2, "scores": [FakeNpFloat(0.0), FakeNpFloat(1.0), FakeNpFloat(0.5)],
                       "objective_scores": [{"em": 0.0}, {"em": 1.0}, {"em": 0.5}],
                       "parent_ids": (2,), "is_seed_candidate": False, "outputs": ["HUGE"], "trajectories": ["HUGE"]})
log.on_reflective_dataset_built({"iteration": 7, "candidate_idx": 2, "components": ["program"],
    "dataset": {"program": [
        {"Inputs": "q1", "Generated Outputs": "a1", "Feedback": "Missed doc D17; gold answer needs entity X."},
        {"Inputs": "q2", "Generated Outputs": "a2", "Feedback": "No solution found."},
    ]}})
log.on_proposal_end({"iteration": 7, "new_instructions": {"program": "better"},
                     "prompts": {"program": "reflect on..."}, "raw_lm_outputs": {"program": "raw"}})
log.on_candidate_rejected({"iteration": 7, "old_score": 0.61, "new_score": 0.61, "reason": "did_not_improve"})
log.on_valset_evaluated({"iteration": 9, "candidate_idx": 3, "average_score": FakeNpFloat(0.66),
                         "scores_by_val_id": {0: 1.0, 1: 0.0, 2: FakeNpFloat(1.0)}, "parent_ids": (2,),
                         "is_best_program": True, "num_examples_evaluated": 100, "total_valset_size": 100,
                         "outputs_by_val_id": {0: "HUGE"}})
log.on_candidate_accepted({"iteration": 9, "new_candidate_idx": 3, "new_score": FakeNpFloat(0.66), "parent_ids": (2,)})
log.on_iteration_end({"iteration": 9, "proposal_accepted": True, "state": FakeState()})  # state must be ignored
log.on_optimization_end({"best_candidate_idx": 3, "total_iterations": 10, "total_metric_calls": 1234,
                         "final_state": FakeState()})  # final_state must be ignored
log.close()

# 3) read back + assert
lines = [json.loads(l) for l in open(path) if l.strip()]
events = [r["event"] for r in lines]
print("events written:", events)
assert events[0] == "meta" and lines[0]["schema_version"] == 1
by = {r["event"]: r for r in lines}
# SI captured verbatim
si = by["reflective_dataset_built"]["dataset"]["program"][0]["Feedback"]
assert si.startswith("Missed doc D17"), si
# numpy-like coerced to real numbers, not stringified
assert by["candidate_selected"]["score"] == 0.61
assert by["evaluation_end"]["scores"] == [0.0, 1.0, 0.5]
assert by["valset_evaluated"]["average_score"] == 0.66
# tuple parent_ids -> list
assert by["candidate_accepted"]["parent_ids"] == [2]
# huge fields dropped
assert "outputs" not in by["evaluation_end"] and "trajectories" not in by["evaluation_end"]
assert "outputs_by_val_id" not in by["valset_evaluated"]
# non-serializable state never leaked a key
assert "state" not in by["iteration_end"] and "final_state" not in by["optimization_end"]
print("\nALL ASSERTIONS PASSED")
print("\nsample line (reflective_dataset_built):")
print(json.dumps(by["reflective_dataset_built"], indent=2)[:600])
