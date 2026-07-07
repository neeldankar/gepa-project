"""Per-event selection scorers for Phase-1 screening.

An EVENT = (run, reflection cycle, minibatch example position p). The event's trainset index
is c.minibatch_ids[p] (positional); its failed constraints are c.failed_ids_per_example[p];
its parent's valset vector is run.valset_by_candidate[c.parent_id]. Each scorer returns one
float per event; build_event_matrix assembles them into analysis/scorers.parquet (gitignored).

Wave 1 (here): valset-prevalence, constraint-tractability, input-typicality, the two
headroom-powered (contaminated) siblings, parent near-frontier opportunity, pool-disagreement
VOI. Waves 2-3 are appended by their own modules/runners.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from gepa_si.screen.corpus_io import RunData, load_corpus
from gepa_si.screen.fungibility import pool_matrix
from gepa_si.screen import scorer_inputs as si

SCORERS_PARQUET = "analysis/scorers.parquet"
KNN_K = 5
EVENT_KEYS = ["seed", "b", "iteration", "example_pos"]

WAVE1_COLS = [
    "valset_prevalence", "constraint_tractability", "input_typicality",
    "prevalence_x_headroom", "typicality_x_headroom",
    "parent_near_frontier", "pool_disagreement_voi",
]


# ---------- static precompute (corpus-wide, once) ----------
class StaticCtx:
    def __init__(self):
        vm = si.valset_meta()
        self.prevalence = vm["prevalence"]
        self.val_constraint_sets = vm["constraint_sets"]
        self.val_ids = vm["val_ids"]                 # ["0".."149"]
        self.n_val = vm["n"]
        # cid -> array of val indices whose spec contains cid
        valids_with: dict[str, list[int]] = {}
        for i, cs in enumerate(self.val_constraint_sets):
            for cid in cs:
                valids_with.setdefault(cid, []).append(i)
        self.valids_with = {c: np.array(v, dtype=int) for c, v in valids_with.items()}
        # embeddings
        self.train_inputs = si.trainset_meta()["inputs"]
        self.train_mat = si.embed_inputs(self.train_inputs)   # (n_train, d)
        self.val_mat = si.valset_input_matrix()               # (150, d)
        # precompute each train row's k nearest valset (idx, sim)
        self._knn: dict[int, tuple[np.ndarray, np.ndarray]] = {}

    def knn(self, train_idx: int) -> tuple[np.ndarray, np.ndarray]:
        if train_idx not in self._knn:
            sims, idx = si.topk_cosine(self.train_mat[train_idx], self.val_mat, KNN_K)
            self._knn[train_idx] = (sims, idx)
        return self._knn[train_idx]


# ---------- per-run precompute ----------
class RunCtx:
    def __init__(self, run: RunData, S: StaticCtx):
        M, idxs = pool_matrix(run)          # (n_pool, 150) aligned to sorted val_ids (int order)
        self.M = M
        self.B = M.max(axis=0)              # pool-best per valset cell
        self.idxs = idxs
        self.run = run
        self._pvec: dict[int, np.ndarray] = {}
        self.S = S

    def parent_vec(self, parent_id: int) -> np.ndarray:
        if parent_id not in self._pvec:
            sbv = self.run.valset_by_candidate[parent_id]
            self._pvec[parent_id] = np.array([sbv[k] for k in self.S.val_ids], dtype=float)
        return self._pvec[parent_id]


# ---------- Wave 1 scorers (per event) ----------
def s_valset_prevalence(failed: list[str], S: StaticCtx) -> float:
    return float(sum(S.prevalence.get(si._strip(c), 0.0) for c in failed))


def s_constraint_tractability(failed: list[str], S: StaticCtx) -> float:
    return float(sum(si.tractability_of(c) for c in failed))


def s_input_typicality(train_idx: int, S: StaticCtx) -> float:
    sims, _ = S.knn(train_idx)
    return float(sims.mean())


def s_prevalence_x_headroom(failed: list[str], R: RunCtx, S: StaticCtx) -> float:
    """Sum over failed constraints of summed valset frontier-deficit on specs carrying them."""
    tot = 0.0
    for c in failed:
        ids = S.valids_with.get(si._strip(c))
        if ids is not None and ids.size:
            tot += float(np.sum(1.0 - R.B[ids]))
    return tot


def s_typicality_x_headroom(train_idx: int, R: RunCtx, S: StaticCtx) -> float:
    """k nearest valset neighbors weighted by their frontier deficit (1 - pool_best)."""
    sims, idx = S.knn(train_idx)
    return float(np.sum(sims * (1.0 - R.B[idx])))


def s_parent_near_frontier(failed: list[str], parent_id: int, R: RunCtx, S: StaticCtx) -> float:
    """Opportunity coords: B_i<1 and parent close behind frontier (small B_i-p_i).

    Score by overlap of the event's failed constraints with those opportunity specs.
    Uses the parent vector p (marginal to THIS parent); excludes the event's own before-score.
    """
    p = R.parent_vec(parent_id)
    w = np.where(R.B < 1.0, np.clip(1.0 - (R.B - p), 0.0, 1.0), 0.0)  # per valset coord
    fset = {si._strip(c) for c in failed}
    if not fset:
        return 0.0
    tot = 0.0
    for c in fset:
        ids = S.valids_with.get(c)
        if ids is not None and ids.size:
            tot += float(np.sum(w[ids]))
    return tot


def s_pool_disagreement_voi(train_idx: int, R: RunCtx, S: StaticCtx) -> float:
    """Mean (over e's k nearest valset cells) of the pool-candidate score variance at that cell."""
    _, idx = S.knn(train_idx)
    if R.M.shape[0] < 2:
        return 0.0
    cell_var = R.M[:, idx].var(axis=0)   # variance across candidates per neighbor cell
    return float(cell_var.mean())


# ---------- event matrix builder ----------
def build_event_matrix(runs: list[RunData] | None = None) -> pd.DataFrame:
    """One row per event with Wave-1 scorer columns. Does not write."""
    if runs is None:
        runs = load_corpus()
    S = StaticCtx()
    rows = []
    for run in runs:
        R = RunCtx(run, S)
        for c in run.cycles:
            for p, failed in enumerate(c.failed_ids_per_example):
                j = c.minibatch_ids[p]
                rows.append({
                    "seed": run.seed, "b": run.b, "iteration": c.iteration, "example_pos": p,
                    "trainset_idx": j,
                    "valset_prevalence": s_valset_prevalence(failed, S),
                    "constraint_tractability": s_constraint_tractability(failed, S),
                    "input_typicality": s_input_typicality(j, S),
                    "prevalence_x_headroom": s_prevalence_x_headroom(failed, R, S),
                    "typicality_x_headroom": s_typicality_x_headroom(j, R, S),
                    "parent_near_frontier": s_parent_near_frontier(failed, c.parent_id, R, S),
                    "pool_disagreement_voi": s_pool_disagreement_voi(j, R, S),
                })
    return pd.DataFrame(rows)
