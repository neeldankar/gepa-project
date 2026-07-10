"""State-dependent selection — the novelty scorer, re-implemented from the frozen screen.

Design v2 §5. The screen's code path CANNOT be imported: `screen_part3_features.py` instantiates
the embedding model at module top level (:33-40), the k-NN is three inline lines inside a loop
(:237-243), and `variant_texts` is nested inside `main()` (:116-119). Refactoring those files is
forbidden by the standing do-not list. So v2 replaces *code-path identity* with *verified output
identity*: this module must reproduce `knn_emb_fb_min` for all 235 non-NaN screen events to
< 1e-12 against the committed `analysis/hover_screen/features.csv`.

  Gate:  analysis/state_dep/verify_novelty.py     (STOP on any mismatch)
  Gate:  analysis/state_dep/embed_sample.py       (cross-venv allclose)

Every function below carries the screen line it mirrors. Do not "improve" any of them.

Run under analysis/state_dep/.venv-armT/bin/python.
"""
from __future__ import annotations

import os
import random

import numpy as np

# --- Embedding pin (design v2 §0). The screen pinned neither revision nor offline mode; its
# reproducibility rests on the local cache holding this snapshot. We pin both.
MODEL_NAME = "all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
WEIGHTS_SHA256 = "53aa51172d142c89d9012cce15ae4d6cc0ca6895895114379cacb4fab128d9db"
WEIGHTS_BYTES = 90_868_376

K_NEIGHBOURS = 3  # screen: np.sort(s)[-3:]


def load_embedder(plain: bool = False):
    """Load the sentence-transformer.

    plain=True reproduces the screen's own unpinned call (`SentenceTransformer("all-MiniLM-L6-v2")`,
    screen_part3_features.py:35) and exists only so the cross-venv gate can compare a pinned load in
    .venv-armT against the screen's actual load in .venv-screen.
    """
    from sentence_transformers import SentenceTransformer

    if plain:
        return SentenceTransformer(MODEL_NAME)
    return SentenceTransformer(
        f"sentence-transformers/{MODEL_NAME}",
        revision=MODEL_REVISION,
        local_files_only=True,
    )


def feedback_text(blk: dict) -> str:
    """The feedback-only variant. Mirrors screen_part3_features.py:117 (`fb = blk["Feedback"]`)."""
    return blk["Feedback"]


def full_text(blk: dict) -> str:
    """Mirrors screen_part3_features.py:118."""
    return blk["Inputs"] + "\n" + blk["Generated Outputs"] + "\n" + blk["Feedback"]


def encode(model, texts: list[str]) -> np.ndarray:
    """Mirrors screen_part3_features.py:129 exactly, including batch_size.

    sentence_transformers sorts inputs by length internally, so batch composition can perturb the
    last bits of the output. The verifier therefore hands this function the *same* interleaved
    (fb, full) text list the screen built, in the same order.
    """
    return model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)


def knn_novelty(query_emb: np.ndarray, archive_embs: np.ndarray | None) -> float:
    """Mean (1 - cosine) over the k=3 nearest strictly-prior archive blocks.

    Mirrors screen_part3_features.py:237-243:

        if n_arch >= 3:
            A = np.stack(arch_emb[var])
            s = A @ emb[(pid, slot, var)]
            knn_e[var].append(float(np.mean(1 - np.sort(s)[-3:])))
        else:
            knn_e[var].append(np.nan)

    Embeddings are L2-normalized at encode time, so the dot product IS cosine.
    Fewer than k prior blocks -> NaN. Only ordinal-0 events hit that branch (the archive grows by
    3 per prior event).
    """
    n_arch = 0 if archive_embs is None else len(archive_embs)
    if n_arch < K_NEIGHBOURS:
        return float("nan")
    A = np.stack(archive_embs)
    s = A @ query_emb
    return float(np.mean(1 - np.sort(s)[-K_NEIGHBOURS:]))


def batch_min(vals) -> float:
    """The `_min` of `knn_emb_fb_min`: min over the <=3 batch members, NaNs dropped.

    Mirrors screen_part3_features.py:43-51 (`agg`). This is a BATCH-level aggregation, not a min
    over the k neighbours.
    """
    v = np.array(
        [x for x in vals if x is not None and not (isinstance(x, float) and np.isnan(x))],
        dtype=float,
    )
    if not len(v):
        return float("nan")
    return float(v.min())


def select_top3(novelties: list[float], rng: random.Random) -> tuple[list[int], dict]:
    """Arm T's selector: the 3 highest-novelty members of the 6 (design v2 §4, §5; review R5-a).

    The subset objective "maximize the minimum member novelty" over C(6,3) subsets is ALWAYS
    maximized by the 3 highest-novelty items, because novelty is a fixed per-item score with no
    within-batch term: the min of the top 3 dominates the min of every other 3-subset. So this is a
    sort, not an enumeration -- identical output, fewer lines, fewer bugs.

    Tie-break cascade (§5). Exact ties at the 3rd/4th boundary are genuinely possible: identical
    missed-title sets render to identical feedback strings, whose embedding distance is 0 by
    construction. At such a tie the "larger sum of member novelties" criterion cannot discriminate
    (the tied candidates carry equal novelty, so every completion has the same sum), so the cascade
    falls through to the seeded RNG. Ties among the tied are broken by rng.sample over the tied
    index set, which is deterministic given (seed, arm).

    Returns (chosen_idx sorted ascending, rationale) -- rationale is persisted per v2 §12.
    """
    order = sorted(range(len(novelties)), key=lambda i: (-novelties[i], i))
    boundary = novelties[order[2]]
    tied = [i for i in order if novelties[i] == boundary]
    strictly_above = [i for i in order[:3] if novelties[i] > boundary]

    tie_broken = False
    if len(tied) > 1 and len(strictly_above) < 3:
        tie_broken = True
        need = 3 - len(strictly_above)
        picked = rng.sample(sorted(tied), need)
        chosen = strictly_above + picked
    else:
        chosen = order[:3]

    rationale = {
        "novelties": [float(x) for x in novelties],
        "sorted_desc_idx": order,
        "boundary_value": float(boundary),
        "tie_at_boundary": tie_broken,
        "tied_idx": sorted(tied) if tie_broken else [],
        "chosen_idx": sorted(chosen),
        "selected_min": float(min(novelties[i] for i in chosen)),
    }
    return sorted(chosen), rationale


def select_random3(n: int, rng: random.Random) -> tuple[list[int], dict]:
    """Arm C's selector: 3 of n uniformly at random from an arm-specific seeded stream.

    Also arm T's cold-start rule at ordinal 0 (empty archive). Per review M3, T and C draw their
    event-1 pick from the SAME derived substream, so they choose identically at event 1 given the
    same seed. The stream is a separate random.Random object and never touches gepa's shared
    `random.Random(seed)` (design v2 §7a) -- otherwise T and C would diverge in the shared stream
    and the pairing would be damaged.
    """
    chosen = sorted(rng.sample(range(n), 3))
    return chosen, {"chosen_idx": chosen, "rule": "uniform_random_3_of_%d" % n}


def verify_weights_on_disk() -> dict:
    """Hash the pinned weights file. Called at run start; recorded in the manifest (v2 §12)."""
    import hashlib

    path = os.path.expanduser(
        "~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2/"
        f"snapshots/{MODEL_REVISION}/model.safetensors"
    )
    real = os.path.realpath(path)
    with open(real, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    size = os.path.getsize(real)
    return {
        "path": path,
        "sha256": digest,
        "bytes": size,
        "sha256_ok": digest == WEIGHTS_SHA256,
        "bytes_ok": size == WEIGHTS_BYTES,
    }
