"""Shared dose acquisition: re-execute a parent candidate and render its feedback blocks.

Used by BOTH dose consumers, so they cannot drift apart:

    dose_control.py --run    the within-session reproducibility control (v2.2 §11-0)
    dose_compute.py --live   the 235-event, 6-candidate re-derivation that yields D

This is the same discipline `eval_split.py` applies to the two §8b consumers, and for the same
reason: two callers of one measurement must not each grow their own copy of it.

WHY THIS MODULE EXISTS AT ALL. The swap evaluated the parent on all 6 drawn candidates
(`hover_swap_run.py:191`) but called `make_reflective_dataset` on only 3 of them (`:199-201`), so
3 of every event's 6 feedback texts were never rendered and never persisted. Their IDENTITY is
fully recoverable -- `pairing_plan.jsonl` carries `draw6_pos` for all 243 events -- but their TEXT
has to be re-derived by re-executing the parent. That re-execution is the dose's whole cost.

v2.2: ALL SIX ARE RE-DERIVED, not three. Under v2.1 the dose mixed 3 texts persisted on
2026-07-09 with 3 re-derived today, and required a 90/90 byte-exact control to license the mix.
That control could not pass -- temp-0 re-execution of this 3-hop program is measurably not
byte-stable (15/24 blocks reproduced across three same-venv re-runs on disk, 2026-08-03) -- and
the mix was unsound anyway: the 3 persisted blocks were `multiset_match`-SELECTED to match the
parent's score profile on A_e (`hover_swap_run.py:192-195`), so they were never an exchangeable
half of the 6, and the x_(4) order statistic sat exactly on that boundary. One self-consistent
execution of all 6 removes both problems and compares nothing to the old run.

FIDELITY. Everything here is imported from `hover_swap_run`, not copied: the mmap-patched probe,
`build_student`, `make_metric`, `_fbmap`, `load_seed`, `reflect_in_instr`, `byte_verify`,
`seed_of`. Importing it also installs the `probe.load_index` mmap monkeypatch (`:30-37`) and the
litellm wire-cost callback. The only thing this module constructs itself is the adapter, verbatim
from `hover_swap_run.py:186-190`.

INTERPRETER. Run under `scratch/hover_probe/.venv/bin/python`, the venv the swap itself ran on --
byte-identical to `.venv-armT` on dspy 3.2.1 / gepa 0.0.27 / litellm / openai / numpy / bm25s /
PyStemmer / Python 3.12.13. Library drift is then not a variable. Novelty SCORING runs separately
under `.venv-armT` (sentence-transformers is not installed here), exactly the split
`verify_novelty.py` already uses.

Nothing here holds a gate. The callers do, because the gate is per-spend-decision.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SWAP = os.path.join(REPO, "analysis", "ablation", "hover_swap")
SCREEN = os.path.join(REPO, "analysis", "hover_screen")
PAIRS = os.path.join(SWAP, "pairs")
FEATURES = os.path.join(SCREEN, "features.csv")
PLAN = os.path.join(SWAP, "pairing_plan.jsonl")


def bootstrap():
    """Import the swap harness (installs the mmap patch) and dspy. Returns (dspy, hover_swap_run).

    `hover_swap_run` is import-safe: everything below its `if __name__ == "__main__"` guard at
    :262 is a def, and its module-level work is exactly what we want -- sys.path for probe, the
    `probe.load_index` mmap monkeypatch, and the litellm cost callback.
    """
    for p in (SWAP, SCREEN, HERE):
        if p not in sys.path:
            sys.path.insert(0, p)
    os.chdir(os.path.join(REPO, "scratch", "hover_probe"))  # probe resolves paths relatively
    import dspy  # noqa: PLC0415

    import hover_swap_run as hs  # noqa: PLC0415

    return dspy, hs


def setup_adapter(dspy, hs):
    """The swap's own context plus a live DspyAdapter factory. Verbatim hover_swap_run.py:186-190."""
    ctx = hs.setup(dspy)  # _load_env, assert_mmap, student, metric, task+reflection LM, plan

    def make_adapter(seed: int, trace_i: int):
        from dspy.teleprompt.gepa.gepa_utils import DspyAdapter  # noqa: PLC0415

        return DspyAdapter(
            student_module=ctx["student"], metric_fn=ctx["metric"],
            feedback_map={k: hs._fbmap(ctx["metric"], k, p)
                          for k, p in ctx["student"].named_predictors()},
            failure_score=0.0, num_threads=hs.NUM_THREADS,
            add_format_failure_as_feedback=False,
            rng=random.Random(hs.seed_of(seed, trace_i)),
            reflection_lm=ctx["reflection_lm"], reflection_minibatch_size=3)

    ctx["make_adapter"] = make_adapter
    return ctx


# --------------------------------------------------------------------------- the event set
def event_rows() -> list[dict]:
    """The 235 dose events, from the screen's own features.csv.

    EVENT_SET is 235, not 243 (v2.1 §20-2): the 8 ordinal-0 events have no k=3 archive and so no
    defined novelty, and 235 is the frame BETA was estimated on. The discriminator is a non-empty
    `knn_emb_fb_min`, which is exactly that condition as the screen itself recorded it.
    """
    import csv  # noqa: PLC0415

    with open(FEATURES, newline="", encoding="utf-8") as fh:
        rows = [r for r in csv.DictReader(fh)]
    keep = [r for r in rows if (r.get("knn_emb_fb_min") or "").strip()]
    assert len(rows) == 243, f"features.csv has {len(rows)} rows, expected 243"
    assert len(keep) == 235, f"{len(keep)} events with novelty, expected 235"
    assert all(int(r["event_ordinal"]) != 0 for r in keep), "an ordinal-0 event carries novelty"
    return keep


def plan_rows() -> dict[tuple[int, int], dict]:
    """pairing_plan.jsonl keyed by (seed, trace_i). Carries draw6_pos, which meta.json does not."""
    out = {}
    with open(PLAN, encoding="utf-8") as fh:
        for line in fh:
            r = json.loads(line)
            out[(int(r["seed"]), int(r["trace_i"]))] = r
    assert len(out) == 243, f"pairing_plan.jsonl has {len(out)} rows, expected 243"
    return out


def positions(pid: str, plan: dict) -> dict:
    """Recover all 6 drawn positions for an event, and which 3 were the persisted (matched) ones.

    The unmatched 3 are `draw6_pos - B_e_pos`, deterministically -- no sampler replay, no RNG.
    Under v2.2 we re-derive all 6 and the split matters only as provenance, but it is recorded so
    the superseded design stays auditable.
    """
    meta = json.load(open(os.path.join(PAIRS, pid, "meta.json")))
    seed, trace_i = int(meta["seed"]), int(meta["trace_i"])
    pr = plan[(seed, trace_i)]
    draw6, b_pos = list(pr["draw6_pos"]), list(meta["B_e_pos"])
    unmatched = [p for p in draw6 if p not in b_pos]
    assert set(b_pos) <= set(draw6), f"{pid}: B_e_pos is not a subset of draw6_pos"
    assert len(unmatched) == 3, f"{pid}: {len(unmatched)} unmatched, expected 3"
    assert not (set(pr["A_e_pos"]) & set(draw6)), f"{pid}: A_e overlaps draw6"
    return {"seed": seed, "trace_i": trace_i, "draw6_pos": draw6, "B_e_pos": b_pos,
            "unmatched_pos": unmatched, "A_e_pos": list(pr["A_e_pos"]),
            "parent_candidate_idx": int(meta["parent_candidate_idx"]), "comp": meta["comp"]}


# --------------------------------------------------------------------------- re-execution
def load_parent(hs, seed: int, trace_i: int):
    """(train, parent_candidate, component, ordinal) for one event. Reuses hover_swap_run.load_seed."""
    d, gr, tm, train, events = hs.load_seed(seed)
    ordinal = next(k for k, e in enumerate(events) if e["i"] == trace_i)
    parent = gr["program_candidates"][events[ordinal]["selected_program_candidate"]]
    finstr = hs.reflect_in_instr(d, ordinal)
    comp = next((n for n, v in parent.items() if v == finstr), None)
    if comp is None:
        raise RuntimeError(f"component match failed seed{seed} trace_i{trace_i}")
    return train, parent, comp, ordinal


def render_feedback(dspy, hs, ctx, seed: int, trace_i: int, train, parent: dict, comp: str,
                    positions_: list[int], arm_tag: str = "SWAP") -> list[str]:
    """Re-execute the parent on `positions_` and return one rendered Feedback string per position.

    SPEND: one metric call per position (3 gen_query + 3 append_notes).

    The rendered path is used rather than a shortcut so this is the same object the screen scored:
    evaluate(capture_traces=True) -> make_reflective_dataset -> IPS.prompt_renderer -> parse_si.
    `adapter.rng` is seeded exactly as the swap seeded it. That seeding governs which trace
    instance is shown under "## Inputs"/"## Generated Outputs"; it does NOT affect Feedback, which
    is `probe.build_si(gold_titles, predicted_titles)` -- a pure function of the retrieved title
    set (`hover_swap_run.make_metric:93-98`). `verify_feedback_is_rng_free` below turns that from
    a claim into a check, for free.
    """
    IPS = ctx["IPS"]
    ex = [dspy.Example(claim=train[p]["claim"], titles=train[p]["gold"]).with_inputs("claim")
          for p in positions_]
    adapter = ctx["make_adapter"](seed, trace_i)
    eb = adapter.evaluate(ex, parent, capture_traces=True)
    adapter.rng = random.Random(hs.seed_of(seed, trace_i, arm_tag))
    rd = adapter.make_reflective_dataset(parent, eb, [comp])
    rendered = IPS.prompt_renderer({"current_instruction_doc": parent[comp],
                                    "dataset_with_feedback": rd[comp]})
    if not hs.byte_verify(rendered):
        raise RuntimeError(f"reflect_in byte-verify FAILED seed{seed} trace_i{trace_i}")

    from screen_part0 import parse_si  # noqa: PLC0415

    blocks = parse_si(rendered, f"seed{seed}_i{trace_i}")
    assert len(blocks) == len(positions_), \
        f"parsed {len(blocks)} blocks for {len(positions_)} positions"
    return [b["Feedback"] for b in blocks]


def verify_feedback_is_rng_free(hs, ctx, eb, parent: dict, comp: str, seed: int, trace_i: int,
                                rendered_feedback: list[str]) -> bool:
    """Confirm Feedback does not depend on adapter.rng, by re-rendering under a different seed.

    $0 -- re-uses the SAME EvaluationBatch, so no LM call. If this ever returns False, the whole
    'rng is irrelevant to the dose' argument is wrong and the caller must stop.
    """
    from screen_part0 import parse_si  # noqa: PLC0415

    IPS = ctx["IPS"]
    adapter = ctx["make_adapter"](seed, trace_i)
    adapter.rng = random.Random(hs.seed_of(seed, trace_i, "RNG-PROBE"))
    rd = adapter.make_reflective_dataset(parent, eb, [comp])
    alt = IPS.prompt_renderer({"current_instruction_doc": parent[comp],
                               "dataset_with_feedback": rd[comp]})
    return [b["Feedback"] for b in parse_si(alt, "rngprobe")] == rendered_feedback


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


# --------------------------------------------------------------------------- worker CLI
def acquire(pids: list[str], outdir: str, passes: int, cap: float) -> int:
    """Re-derive all 6 feedback texts for each pid, `passes` times. LIVE SPEND. Checkpointed.

    Two passes over the SAME events is what makes the v2.2 control possible: it measures this
    program's own within-session reproducibility on the actual dose data, rather than comparing
    today's bytes to 2026-07-09's.
    """
    from gates import require  # noqa: PLC0415

    require("APPROVED-dose")
    os.makedirs(outdir, exist_ok=True)
    dspy, hs = bootstrap()
    ctx = setup_adapter(dspy, hs)
    plan = plan_rows()
    lm = ctx["dspy"].settings.lm
    rng_checked = False

    def spend() -> float:
        tot = 0.0
        for h in list(lm.history):
            u = h.get("usage") or {}
            tot += (u.get("prompt_tokens", 0) * hs.probe.PRICE_IN
                    + u.get("completion_tokens", 0) * hs.probe.PRICE_OUT)
        return tot

    done = 0
    for pid in pids:
        ck = os.path.join(outdir, f"{pid}.json")
        if os.path.exists(ck):
            done += 1
            continue
        pos = positions(pid, plan)
        seed, trace_i = pos["seed"], pos["trace_i"]
        train, parent, comp, ordinal = load_parent(hs, seed, trace_i)
        rec = {"pid": pid, "seed": seed, "trace_i": trace_i, "ordinal": ordinal, "comp": comp,
               "draw6_pos": pos["draw6_pos"], "B_e_pos": pos["B_e_pos"],
               "parent_candidate_idx": pos["parent_candidate_idx"], "passes": []}
        for k in range(passes):
            fb = render_feedback(dspy, hs, ctx, seed, trace_i, train, parent, comp,
                                 pos["draw6_pos"])
            rec["passes"].append({str(p): t for p, t in zip(pos["draw6_pos"], fb)})
            if not rng_checked:
                # $0 structural check: Feedback must not depend on adapter.rng. Done once --
                # if it holds for one event it holds for all, since it is a property of the
                # metric, not of the data (see render_feedback's docstring).
                ex = [dspy.Example(claim=train[p]["claim"], titles=train[p]["gold"])
                      .with_inputs("claim") for p in pos["draw6_pos"]]
                a = ctx["make_adapter"](seed, trace_i)
                eb = a.evaluate(ex, parent, capture_traces=True)
                ok = verify_feedback_is_rng_free(hs, ctx, eb, parent, comp, seed, trace_i,
                                                 [b for b in rec["passes"][k].values()])
                print(f"  [rng-free check] Feedback independent of adapter.rng: {ok}"
                      f"{'' if ok else '   <-- STRUCTURAL ASSUMPTION VIOLATED'}", flush=True)
                rng_checked = True
        json.dump(rec, open(ck, "w"), indent=2)
        done += 1
        s = spend()
        print(f"  {pid:16} {passes}x6 rendered   ${s:.4f}   [{done}/{len(pids)}]", flush=True)
        if s > cap:
            print(f"\nSPEND TRIPWIRE: ${s:.4f} > cap ${cap:.2f} — aborting. "
                  f"{done}/{len(pids)} checkpointed; re-running resumes at $0.")
            return 1
    print(f"\nacquired {done}/{len(pids)} events x {passes} pass(es) -> {outdir}")
    return 0


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="dose acquisition worker (run under hover_probe/.venv)")
    ap.add_argument("--pids", help="comma-separated pair ids; default = all 235 dose events")
    ap.add_argument("--out", required=True)
    ap.add_argument("--passes", type=int, default=1)
    ap.add_argument("--cap", type=float, required=True)
    a = ap.parse_args()
    ids = a.pids.split(",") if a.pids else [r["pair_id"] for r in event_rows()]
    raise SystemExit(acquire(ids, a.out, a.passes, a.cap))
