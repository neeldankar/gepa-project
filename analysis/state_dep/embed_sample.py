"""ACCEPTANCE GATE part 1 (design v2 §5, §13-2): cross-venv embedding equivalence.

Neel's condition on the environment move: the new .venv-armT must reproduce the embeddings that
.venv-screen produced, because the screen's novelty numbers came from that stack and embedding
output can drift across sentence-transformers / torch versions.

Encode a fixed, deterministic sample of real archive feedback texts and dump them to .npy.
Run once under EACH venv, then compare:

    analysis/state_dep/.venv-armT/bin/python analysis/state_dep/embed_sample.py \
        --out /tmp/emb_armT.npy                       # pinned load (revision + local_files_only)

    analysis/hover_screen/.venv-screen/bin/python analysis/state_dep/embed_sample.py \
        --out /tmp/emb_screen.npy --plain             # the screen's own unpinned call

    analysis/state_dep/.venv-armT/bin/python analysis/state_dep/embed_sample.py \
        --compare /tmp/emb_armT.npy /tmp/emb_screen.npy

`--plain` reproduces `SentenceTransformer("all-MiniLM-L6-v2")` exactly as
screen_part3_features.py:35 calls it, so the comparison answers the real question: does the pinned
load in the new venv match the screen's actual load?

$0: local model only, no API calls. Read-only on the frozen corpora.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SCREEN = os.path.join(REPO, "analysis", "hover_screen")
PAIRS = os.path.join(REPO, "analysis", "ablation", "hover_swap", "pairs")

sys.path.insert(0, HERE)
sys.path.insert(0, SCREEN)

N_PAIRS = 8  # first 8 pair dirs in the screen's own sorted order -> 24 feedback blocks


def sample_texts() -> list[str]:
    """Deterministic: the feedback blocks of the first N_PAIRS pair dirs, screen's sort order."""
    from screen_part0 import parse_si  # import-clean

    texts = []
    for pid in sorted(os.listdir(PAIRS))[:N_PAIRS]:
        raw = open(os.path.join(PAIRS, pid, "reflect_in_SAME.txt"), encoding="utf-8").read()
        for blk in parse_si(raw, pid):
            texts.append(blk["Feedback"])
    return texts


def do_encode(out_path: str, plain: bool) -> int:
    from sentence_transformers import SentenceTransformer

    texts = sample_texts()
    joined = "\n\x00\n".join(texts).encode()
    print(f"texts: n={len(texts)}  sha256={hashlib.sha256(joined).hexdigest()}")

    if plain:
        # exactly screen_part3_features.py:35
        model = SentenceTransformer("all-MiniLM-L6-v2")
        how = "plain (screen-style, unpinned)"
    else:
        from novelty import load_embedder

        model = load_embedder()
        how = "pinned (revision + local_files_only)"

    M = model.encode(texts, batch_size=64, show_progress_bar=False, normalize_embeddings=True)
    M = np.asarray(M, dtype=np.float32)
    np.save(out_path, M)

    import sentence_transformers as st
    import torch

    print(f"load: {how}")
    print(f"python {sys.version.split()[0]}  st {st.__version__}  torch {torch.__version__}  numpy {np.__version__}")
    print(f"wrote {out_path}  shape={M.shape}  dtype={M.dtype}")
    return 0


def do_compare(a_path: str, b_path: str) -> int:
    A = np.load(a_path)
    B = np.load(b_path)
    print(f"A {a_path}  shape={A.shape}")
    print(f"B {b_path}  shape={B.shape}")
    if A.shape != B.shape:
        print("\nGATE FAIL: shape mismatch")
        return 1

    d = np.abs(A - B)
    max_abs = float(d.max())
    # the quantity that actually matters downstream is cosine, i.e. the dot product of
    # L2-normalized rows -- so check that too, not just raw coordinates.
    cos = (A * B).sum(axis=1) / (np.linalg.norm(A, axis=1) * np.linalg.norm(B, axis=1))
    min_cos = float(cos.min())

    print(f"\nmax |A-B|            : {max_abs:.3e}")
    print(f"min per-row cosine   : {min_cos:.15f}")
    print(f"np.allclose(atol=1e-6): {np.allclose(A, B, atol=1e-6, rtol=0)}")
    print(f"np.allclose(atol=1e-5): {np.allclose(A, B, atol=1e-5, rtol=0)}")
    print(f"bitwise identical    : {bool((A == B).all())}")

    # Gate: embeddings must agree to well within any tolerance that could move knn_emb_fb_min.
    # knn novelty = mean(1 - cos) over 3 neighbours; a 1e-6 coordinate drift moves it ~1e-6,
    # far below the 1e-12 byte-verify tolerance ONLY if bitwise identical. So we require
    # allclose at 1e-6 to pass the environment move, and report whether it is bit-exact.
    if not np.allclose(A, B, atol=1e-6, rtol=0):
        print("\nGATE FAIL: embeddings differ across venvs beyond 1e-6.")
        print("The environment move does NOT preserve the screen's embedding geometry.")
        return 1

    print("\nGATE PASS: .venv-armT reproduces .venv-screen embeddings.")
    if not (A == B).all():
        print("NOTE: agreement is numerical, not bitwise. verify_novelty.py's 1e-12")
        print("      byte-verify is the binding check on knn_emb_fb_min itself.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out")
    p.add_argument("--plain", action="store_true")
    p.add_argument("--compare", nargs=2, metavar=("A", "B"))
    a = p.parse_args()
    if a.compare:
        raise SystemExit(do_compare(*a.compare))
    if not a.out:
        p.error("need --out or --compare")
    raise SystemExit(do_encode(a.out, a.plain))
