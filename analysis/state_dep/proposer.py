"""Subset-selecting proposer for arms C and T (design v2 §4, §5, §6a).

WHY AN OVERRIDE. gepa 0.0.27's `ReflectiveMutationProposer.propose()` is one monolithic method:
the minibatch ids, the parent rollout, the reflective dataset, the child eval, and the returned
proposal are all locals of a single 250-line function. There is no sub-method seam, and callbacks
are explicitly observational ("cannot modify state", `core/callbacks.py:6-8`). So the 6->3 selection
must live in a `propose()` override. The public `gepa.optimize()` exposes `batch_sampler` but no
proposer, so the runner wires `GEPAEngine` directly (v2 §13-3).

THE INVARIANTS THIS FILE EXISTS TO PRESERVE (v2 §6a item 5; threat §15-11):

  * The parent rolls out all 6, and all 6 are counted   -> `increment_evals(len(subsample_ids))`
                                                            stays at the stock site, value 6.
  * The child is evaluated on the chosen 3 only         -> `cached_evaluate_full(..., chosen_ids)`
                                                            so `actual_evals_count` == 3.
  * Acceptance compares 3-vs-3                          -> `subsample_scores_before/after` are both
                                                            restricted to the chosen 3, and
                                                            `engine.py:490-493` sums only those.
  * The unchosen 3 leak nowhere                         -> Pareto/frontier is updated exclusively
                                                            from valset scores (`state.py:496-532`),
                                                            never from a minibatch. The only place
                                                            they *would* appear is the trace, so the
                                                            trace carries the chosen 3 and the full
                                                            6 go under separate keys (v2 §12).

Line numbers in comments below refer to the stock
`gepa/proposer/reflective_mutation/reflective_mutation.py` (0.0.27).

Run under analysis/state_dep/.venv-armT/bin/python.
"""
from __future__ import annotations

import random
from typing import Any

from gepa.core.adapter import EvaluationBatch
from gepa.core.callbacks import (
    CandidateSelectedEvent,
    EvaluationEndEvent,
    EvaluationSkippedEvent,
    EvaluationStartEvent,
    MinibatchSampledEvent,
    ProposalEndEvent,
    ProposalStartEvent,
    ReflectiveDatasetBuiltEvent,
    notify_callbacks,
)
from gepa.core.state import GEPAState
from gepa.proposer.base import CandidateProposal
from gepa.proposer.reflective_mutation.reflective_mutation import ReflectiveMutationProposer

from novelty import batch_min, encode, knn_novelty, select_random3, select_top3

# v2 §20 open decision 1. `skip_perfect_score` at reflective_mutation.py:204 tests
# `all(s >= perfect_score for s in eval_curr.scores)` -- that is 6 scores in T/C and 3 in B, so the
# arms skip at different rates and a skip in T/C burns 6 counted parent evals against B's 3 (the
# gate sits AFTER the counter increment at :164). There is no defensible default. The runner MUST
# choose, and the choice is pre-registered before APPROVED-liverun.
SKIP_PERFECT_SCOPES = ("all6", "chosen3")


def sub_batch(eb: EvaluationBatch, idxs: list[int]) -> EvaluationBatch:
    """Restrict an EvaluationBatch to `idxs`. Mirrors hover_swap_run.py:149-151."""
    return EvaluationBatch(
        outputs=[eb.outputs[i] for i in idxs],
        scores=[eb.scores[i] for i in idxs],
        trajectories=[eb.trajectories[i] for i in idxs] if eb.trajectories else None,
        objective_scores=[eb.objective_scores[i] for i in idxs] if eb.objective_scores else None,
    )


class SubsetSelectingProposer(ReflectiveMutationProposer):
    """Draw M, roll the parent out on M, choose 3, reflect and accept on those 3.

    arm='C' -> uniform random 3 of M from an arm-specific seeded stream.
    arm='T' -> the 3 highest-novelty members (a sort, not a C(6,3) enumeration; review R5-a).

    Per review M3, T's cold-start pick (ordinal 0, empty archive) uses the SAME derived substream as
    C's picker, so T and C choose identically at event 1 given the same seed.
    """

    def __init__(self, *args, arm: str, seed: int, skip_perfect_scope: str, embedder=None, **kw):
        super().__init__(*args, **kw)
        assert arm in ("C", "T"), arm
        if skip_perfect_scope not in SKIP_PERFECT_SCOPES:
            raise ValueError(
                f"skip_perfect_scope must be one of {SKIP_PERFECT_SCOPES}; got {skip_perfect_scope!r}. "
                "This is v2 §20 open decision 1 and has no default."
            )
        self.arm = arm
        self.seed = seed
        self.skip_perfect_scope = skip_perfect_scope
        self.embedder = embedder  # required for arm T only

        # Arm-specific RNG streams, derived as f(seed, arm), NEVER gepa's shared random.Random(seed)
        # (v2 §7a). The cold-start stream is shared between T and C by construction (M3).
        self.pick_rng = random.Random(f"{seed}|{arm}|pick")
        self.coldstart_rng = random.Random(f"{seed}|coldstart")  # identical across T and C
        self.tiebreak_rng = random.Random(f"{seed}|{arm}|tiebreak")

        # The run's SI archive: feedback texts of the examples ACTUALLY REFLECTED ON (the chosen 3)
        # at strictly-prior events of this run. The unchosen 3 never enter (v2 §5, V1-confirmed).
        self.archive_texts: list[str] = []
        self.archive_embs: list[Any] = []

        self.event_log: list[dict] = []

    # -- novelty ---------------------------------------------------------------------------
    def _novelties(self, feedback_texts: list[str]) -> list[float]:
        """knn_emb_fb per member, against the run's strictly-prior chosen-3 archive."""
        embs = encode(self.embedder, feedback_texts)
        n_arch = len(self.archive_embs)
        return [
            knn_novelty(embs[j], self.archive_embs if n_arch >= 3 else None)
            for j in range(len(feedback_texts))
        ], embs

    def _advance_archive(self, texts: list[str], embs) -> None:
        """STRICTLY after the event is scored and selected (mirrors screen :327-338)."""
        for t, e in zip(texts, embs):
            self.archive_texts.append(t)
            self.archive_embs.append(e)

    # -- the override ----------------------------------------------------------------------
    def propose(self, state: GEPAState) -> CandidateProposal | None:  # noqa: C901
        i = state.i + 1

        # ---- stock :107-129 -------------------------------------------------------------
        curr_prog_id = self.candidate_selector.select_candidate_idx(state)
        curr_prog = state.program_candidates[curr_prog_id]
        state.full_program_trace[-1]["selected_program_candidate"] = curr_prog_id
        self.logger.log(
            f"Iteration {i}: Selected program {curr_prog_id} score: "
            f"{state.program_full_scores_val_set[curr_prog_id]}"
        )
        notify_callbacks(
            self.callbacks,
            "on_candidate_selected",
            CandidateSelectedEvent(
                iteration=i,
                candidate_idx=curr_prog_id,
                candidate=curr_prog,
                score=state.program_full_scores_val_set[curr_prog_id],
            ),
        )
        self.experiment_tracker.log_metrics(
            {
                "iteration": i,
                "selected_program_candidate": curr_prog_id,
                "total_metric_calls": state.total_num_evals,
            },
            step=i,
        )

        # ---- stock :131-144, but the sampler returns M=6 --------------------------------
        subsample_ids = self.batch_sampler.next_minibatch_ids(self.trainset, state)
        minibatch = self.trainset.fetch(subsample_ids)
        notify_callbacks(
            self.callbacks,
            "on_minibatch_sampled",
            MinibatchSampledEvent(
                iteration=i, minibatch_ids=subsample_ids, trainset_size=len(self.trainset)
            ),
        )

        # ---- stock :146-163: parent rollout on ALL M ------------------------------------
        curr_parent_ids = [p for p in state.parent_program_for_candidate[curr_prog_id] if p is not None]
        is_seed_candidate = curr_prog_id == 0
        notify_callbacks(
            self.callbacks,
            "on_evaluation_start",
            EvaluationStartEvent(
                iteration=i,
                candidate_idx=curr_prog_id,
                batch_size=len(minibatch),
                capture_traces=True,
                parent_ids=curr_parent_ids,
                inputs=minibatch,
                is_seed_candidate=is_seed_candidate,
            ),
        )
        eval_curr = self.adapter.evaluate(minibatch, curr_prog, capture_traces=True)

        # ---- stock :164 -- UNCHANGED. The parent legitimately rolled out all 6; all 6 count.
        state.increment_evals(len(subsample_ids))

        notify_callbacks(
            self.callbacks,
            "on_evaluation_end",
            EvaluationEndEvent(
                iteration=i,
                candidate_idx=curr_prog_id,
                scores=eval_curr.scores,
                has_trajectories=bool(eval_curr.trajectories),
                parent_ids=curr_parent_ids,
                outputs=eval_curr.outputs,
                trajectories=eval_curr.trajectories,
                objective_scores=eval_curr.objective_scores,
                is_seed_candidate=is_seed_candidate,
            ),
        )

        # ---- stock :182-187: cache the parent's M evaluations (all M are real, keep them) --
        if state.evaluation_cache is not None:
            objective_scores_list = list(eval_curr.objective_scores) if eval_curr.objective_scores else None
            state.evaluation_cache.put_batch(
                curr_prog, subsample_ids, eval_curr.outputs, eval_curr.scores, objective_scores_list
            )

        # ---- stock :189-202 --------------------------------------------------------------
        if not eval_curr.trajectories or len(eval_curr.trajectories) == 0:
            self.logger.log(f"Iteration {i}: No trajectories captured. Skipping.")
            notify_callbacks(
                self.callbacks,
                "on_evaluation_skipped",
                EvaluationSkippedEvent(
                    iteration=i,
                    candidate_idx=curr_prog_id,
                    reason="no_trajectories",
                    scores=eval_curr.scores,
                    is_seed_candidate=is_seed_candidate,
                ),
            )
            return None

        # ---- stock :204 with v2 §20 open decision 1 -------------------------------------
        if self.skip_perfect_scope == "all6":
            if self.skip_perfect_score and all(s >= self.perfect_score for s in eval_curr.scores):
                self.logger.log(f"Iteration {i}: All {len(eval_curr.scores)} subsample scores perfect. Skipping.")
                notify_callbacks(
                    self.callbacks,
                    "on_evaluation_skipped",
                    EvaluationSkippedEvent(
                        iteration=i,
                        candidate_idx=curr_prog_id,
                        reason="all_scores_perfect",
                        scores=eval_curr.scores,
                        is_seed_candidate=is_seed_candidate,
                    ),
                )
                return None

        # ---- stock :223-230, but rendered over ALL M so novelty can see all M feedbacks ---
        predictor_names_to_update = self.module_selector(
            state, eval_curr.trajectories, eval_curr.scores, curr_prog_id, curr_prog
        )
        try:
            rd_all = self.adapter.make_reflective_dataset(curr_prog, eval_curr, predictor_names_to_update)
        except Exception as e:  # noqa: BLE001
            self.logger.log(f"Iteration {i}: Exception building reflective dataset: {e}")
            return None

        comp = predictor_names_to_update[0]
        if len(rd_all[comp]) != len(subsample_ids):
            # 1:1 alignment between reflective examples and drawn ids is what makes the novelty
            # scores addressable. make_reflective_dataset `continue`s on examples with no matching
            # trace instance (gepa_utils.py:227-228), which would silently shift the mapping.
            self.logger.log(
                f"Iteration {i}: reflective dataset misaligned "
                f"({len(rd_all[comp])} items vs {len(subsample_ids)} ids). Skipping."
            )
            return None

        feedback_texts = [item["Feedback"] for item in rd_all[comp]]

        # ---- THE INTERVENTION: choose 3 of M ---------------------------------------------
        n_arch = len(self.archive_embs)
        novelties, embs = self._novelties(feedback_texts) if self.arm == "T" else (None, None)

        if self.arm == "T" and n_arch >= 3:
            chosen_slots, rationale = select_top3(novelties, self.tiebreak_rng)
            rule = "top3_by_knn_emb_fb"
        elif self.arm == "T":
            # cold start: empty/short archive -> uniform random, from the SHARED substream (M3)
            chosen_slots, rationale = select_random3(len(subsample_ids), self.coldstart_rng)
            rule = "coldstart_random3"
        else:  # arm C
            rng = self.coldstart_rng if state.i == 0 else self.pick_rng
            chosen_slots, rationale = select_random3(len(subsample_ids), rng)
            rule = "coldstart_random3" if state.i == 0 else "uniform_random3"

        chosen_ids = [subsample_ids[j] for j in chosen_slots]
        eval_sel = sub_batch(eval_curr, chosen_slots)

        if self.skip_perfect_scope == "chosen3":
            if self.skip_perfect_score and all(s >= self.perfect_score for s in eval_sel.scores):
                self.logger.log(f"Iteration {i}: All chosen-3 subsample scores perfect. Skipping.")
                notify_callbacks(
                    self.callbacks,
                    "on_evaluation_skipped",
                    EvaluationSkippedEvent(
                        iteration=i,
                        candidate_idx=curr_prog_id,
                        reason="all_scores_perfect",
                        scores=eval_sel.scores,
                        is_seed_candidate=is_seed_candidate,
                    ),
                )
                return None

        # ---- trace fields carry the CHOSEN 3 (v2 §12; screen_part0.py:167-168 asserts b==3) --
        state.full_program_trace[-1]["subsample_ids"] = chosen_ids
        state.full_program_trace[-1]["subsample_scores"] = eval_sel.scores
        # ...the full M go under separate keys, for the second path and the descriptives.
        state.full_program_trace[-1]["statedep_drawn_ids"] = list(subsample_ids)
        state.full_program_trace[-1]["statedep_drawn_scores"] = list(eval_curr.scores)
        state.full_program_trace[-1]["statedep_arm"] = self.arm
        state.full_program_trace[-1]["statedep_archive_size"] = n_arch
        state.full_program_trace[-1]["statedep_rule"] = rule
        state.full_program_trace[-1]["statedep_novelties"] = (
            [float(x) for x in novelties] if novelties is not None else None
        )
        state.full_program_trace[-1]["statedep_selection"] = rationale

        self.experiment_tracker.log_metrics(
            {"subsample_score": sum(eval_sel.scores), "total_metric_calls": state.total_num_evals}, step=i
        )

        # ---- stock :228-283, but on the chosen 3 only ------------------------------------
        rd_sel = {comp: [rd_all[comp][j] for j in chosen_slots]}
        rd_concrete: dict[str, list[dict[str, Any]]] = {k: [dict(x) for x in v] for k, v in rd_sel.items()}
        try:
            notify_callbacks(
                self.callbacks,
                "on_reflective_dataset_built",
                ReflectiveDatasetBuiltEvent(
                    iteration=i,
                    candidate_idx=curr_prog_id,
                    components=predictor_names_to_update,
                    dataset=rd_concrete,
                ),
            )
            notify_callbacks(
                self.callbacks,
                "on_proposal_start",
                ProposalStartEvent(
                    iteration=i,
                    parent_candidate=curr_prog,
                    components=predictor_names_to_update,
                    reflective_dataset=rd_concrete,
                ),
            )
            new_texts = self.propose_new_texts(curr_prog, rd_sel, predictor_names_to_update)
            notify_callbacks(
                self.callbacks, "on_proposal_end", ProposalEndEvent(iteration=i, new_instructions=new_texts)
            )
            for pname, text in new_texts.items():
                self.logger.log(f"Iteration {i}: Proposed new text for {pname}: {text}")
            self.experiment_tracker.log_metrics(
                {f"new_instruction_{pname}": text for pname, text in new_texts.items()}, step=i
            )
        except Exception as e:  # noqa: BLE001
            self.logger.log(f"Iteration {i}: Exception during reflection/proposal: {e}")
            import traceback

            self.logger.log(traceback.format_exc())
            return None

        # ---- stock :285-293 --------------------------------------------------------------
        new_candidate = curr_prog.copy()
        for pname, text in new_texts.items():
            assert pname in new_candidate, f"{pname} missing in candidate"
            new_candidate[pname] = text

        def evaluator(b, c):
            r = self.adapter.evaluate(b, c, capture_traces=False)
            return r.outputs, r.scores, list(r.objective_scores) if r.objective_scores else None

        # ---- stock :296-333, but the CHILD sees only the chosen 3 -------------------------
        chosen_minibatch = self.trainset.fetch(chosen_ids)
        notify_callbacks(
            self.callbacks,
            "on_evaluation_start",
            EvaluationStartEvent(
                iteration=i,
                candidate_idx=None,
                batch_size=len(chosen_minibatch),
                capture_traces=False,
                parent_ids=[curr_prog_id],
                inputs=chosen_minibatch,
                is_seed_candidate=False,
            ),
        )
        outputs_by_id, scores_by_id, objective_by_id, actual_evals_count = state.cached_evaluate_full(
            new_candidate, chosen_ids, self.trainset.fetch, evaluator
        )
        new_scores = [scores_by_id[eid] for eid in chosen_ids]
        outputs = [outputs_by_id[eid] for eid in chosen_ids]
        notify_callbacks(
            self.callbacks,
            "on_evaluation_end",
            EvaluationEndEvent(
                iteration=i,
                candidate_idx=None,
                scores=new_scores,
                has_trajectories=False,
                parent_ids=[curr_prog_id],
                outputs=outputs,
                trajectories=None,
                objective_scores=[objective_by_id[eid] for eid in chosen_ids] if objective_by_id else None,
                is_seed_candidate=False,
            ),
        )

        # ---- stock :332 -- child counts 3, not M (no cache hit for a brand-new candidate) --
        state.increment_evals(actual_evals_count)
        state.full_program_trace[-1]["new_subsample_scores"] = new_scores

        self.experiment_tracker.log_metrics(
            {"new_subsample_score": sum(new_scores), "total_metric_calls": state.total_num_evals}, step=i
        )

        # ---- archive advances STRICTLY after the event is scored and selected (screen :327) --
        chosen_texts = [feedback_texts[j] for j in chosen_slots]
        if self.arm == "T":
            self._advance_archive(chosen_texts, [embs[j] for j in chosen_slots])
        else:
            # Arm C maintains and logs the same archive for descriptive symmetry, but never selects
            # on it (v2 §5). Embeddings only computed if an embedder was supplied.
            if self.embedder is not None:
                sel_embs = encode(self.embedder, chosen_texts)
                self._advance_archive(chosen_texts, list(sel_embs))
            else:
                self.archive_texts.extend(chosen_texts)

        self.event_log.append(
            {
                "iteration": i,
                "arm": self.arm,
                "drawn_ids": list(subsample_ids),
                "drawn_scores": list(eval_curr.scores),
                "chosen_ids": chosen_ids,
                "chosen_scores": list(eval_sel.scores),
                "child_scores": list(new_scores),
                "archive_size_at_scoring": n_arch,
                "rule": rule,
                "selection": rationale,
                "novelty_min_chosen": batch_min([novelties[j] for j in chosen_slots]) if novelties else None,
                "parent_evals_counted": len(subsample_ids),
                "child_evals_counted": actual_evals_count,
                "total_num_evals_after": state.total_num_evals,
            }
        )

        # ---- stock :340-347: acceptance sees ONLY the chosen 3 on both sides ---------------
        return CandidateProposal(
            candidate=new_candidate,
            parent_program_ids=[curr_prog_id],
            subsample_indices=chosen_ids,
            subsample_scores_before=eval_sel.scores,
            subsample_scores_after=new_scores,
            tag="reflective_mutation",
        )
