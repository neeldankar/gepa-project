"""HoVer batch-swap feasibility inventory — offline probe (read-only, $0, no network).

Computes the 1b field census, 1c pair counts, 1d id-resolve rate, and 1e score
statistics for the frozen HoVer logs, reading LOCAL JSON ONLY. It never imports
the DSPy program, never calls an LM, and never touches HuggingFace — run with
HF_DATASETS_OFFLINE=1. Frozen corpora are read-only; this script only reads.

  HF_DATASETS_OFFLINE=1 python3 scripts/hover_swap_inventory_probe.py

Pairing criteria are the v2 criteria read from scripts/batch_swap_v2_run.py
(:157-173): same run/seed, same tercile, disjoint minibatches, parent text
available, failure-match (>=2 of 3 examples score <1.0 under the parent). The
v2 failure-match re-evaluates parent P_B on B''s batch (a live cross-eval that
is NOT available offline); the offline proxy here uses each batch's OWN logged
parent subsample_scores. type_jaccard is a v2 covariate, not a pairing filter,
and has no HoVer analogue in the logs.
"""
import json
import math
import os
import statistics as st

ROOT = os.path.join(os.path.dirname(__file__), "..")
HP = os.path.join(ROOT, "scratch", "hover_probe")


def load_json(*parts):
    with open(os.path.join(HP, *parts)) as f:
        return json.load(f)


def dist(vals):
    """mean/sd/min/max + fraction at floor(0.0)/ceiling(1.0)."""
    n = len(vals)
    if n == 0:
        return {"n": 0}
    return {
        "n": n,
        "mean": round(st.mean(vals), 4),
        "sd": round(st.pstdev(vals), 4) if n > 1 else 0.0,
        "min": round(min(vals), 4),
        "max": round(max(vals), 4),
        "frac_floor_0": round(sum(1 for v in vals if v == 0.0) / n, 4),
        "frac_ceil_1": round(sum(1 for v in vals if v == 1.0) / n, 4),
    }


def terciles(iters):
    """Replicate v2 tercile assignment (batch_swap_v2_run.py:111-114)."""
    q1, q2 = (
        _quantile(iters, 1 / 3),
        _quantile(iters, 2 / 3),
    )
    return {it: (0 if it <= q1 else (1 if it <= q2 else 2)) for it in iters}


def _quantile(xs, q):
    """Linear-interpolation quantile matching numpy.quantile default."""
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    pos = q * (len(s) - 1)
    lo = math.floor(pos)
    hi = math.ceil(pos)
    if lo == hi:
        return s[lo]
    return s[lo] + (s[hi] - s[lo]) * (pos - lo)


def census_run(name):
    """Field-presence flags for one run dir; returns dict field->status."""
    try:
        res = load_json(name, "gepa_result.json")
    except FileNotFoundError:
        res = None
    try:
        refl = load_json(name, "reflections.json")
    except FileNotFoundError:
        refl = None
    has_trace = bool(res and res.get("full_program_trace"))
    tr = res.get("full_program_trace", []) if res else []
    n_ev = len(tr)
    fields = {}
    fields["n_events"] = n_ev
    fields["parent_program_text_all_modules"] = (
        "present" if res and res.get("program_candidates")
        and all(len(c) >= 2 for c in res["program_candidates"]) else "absent"
    )
    fields["minibatch_ids"] = "present" if has_trace and all("subsample_ids" in e for e in tr) else "absent"
    fields["minibatch_content_inputs"] = "present" if refl else "absent"  # embedded in reflection prompt/reflect_in
    fields["generated_outputs"] = "present" if refl else "absent"          # embedded in reflection prompt
    fields["SI_feedback_text"] = "present" if refl else "absent"           # embedded in reflection prompt
    fields["per_example_parent_scores"] = "present" if has_trace and all("subsample_scores" in e for e in tr) else "absent"
    fields["per_example_child_scores"] = "present" if has_trace and all("new_subsample_scores" in e for e in tr) else "absent"
    fields["child_program_text"] = "present" if refl and all("output" in r for r in refl) else "absent"
    fields["accept_decision"] = "absent (inferred)"  # no accept key in trace anywhere
    fields["valset_scores"] = (
        "per-candidate only" if res and res.get("prog_candidate_val_subscores") else "absent"
    )
    # b constant?
    if has_trace:
        bs = {len(e["subsample_ids"]) for e in tr}
        fields["b_values"] = sorted(bs)
        fields["b_constant"] = len(bs) == 1
    return fields


def pairability(name):
    res = load_json(name, "gepa_result.json")
    tr = res["full_program_trace"]
    n_cand = len(res.get("program_candidates", []))
    events = []
    for e in tr:
        events.append({
            "i": e["i"],
            "ids": set(e["subsample_ids"]),
            "parent": e["selected_program_candidate"],
            "parent_ok": 0 <= e["selected_program_candidate"] < n_cand,
            "fail_proxy": sum(1 for s in e["subsample_scores"] if s < 1.0),  # own-batch parent scores
        })
    its = [e["i"] for e in events]
    terc = terciles(its)

    def count(criteria):
        pairs = 0
        partnered = set()
        for a in range(len(events)):
            for b in range(a + 1, len(events)):
                A, B = events[a], events[b]
                if "disjoint" in criteria and (A["ids"] & B["ids"]):
                    continue
                if "parent" in criteria and not (A["parent_ok"] and B["parent_ok"]):
                    continue
                if "tercile" in criteria and terc[A["i"]] != terc[B["i"]]:
                    continue
                if "failmatch" in criteria and not (A["fail_proxy"] >= 2 and B["fail_proxy"] >= 2):
                    continue
                pairs += 1
                partnered.add(A["i"])
                partnered.add(B["i"])
        return {"eligible_unordered_pairs": pairs, "events_with_ge1_partner": len(partnered)}

    return {
        "n_events": len(events),
        "n_runs": 1,
        "tercile_sizes": {t: sum(1 for i in its if terc[i] == t) for t in (0, 1, 2)},
        "portable_v2_criteria": count({"disjoint", "parent", "tercile", "failmatch"}),
        "weakest_sane": count({"disjoint", "parent"}),
    }


def id_resolve(name, k=20):
    res = load_json(name, "gepa_result.json")
    tr = res["full_program_trace"]
    trainset = res.get("trainset_claims", [])
    all_ids = [i for e in tr for i in e["subsample_ids"]]
    uniq = sorted(set(all_ids))
    spot = uniq[:k]
    resolved = sum(1 for i in spot if 0 <= i < len(trainset) and trainset[i])
    return {
        "n_trainset_claims": len(trainset),
        "unique_ids_used": len(uniq),
        "id_range": [min(all_ids), max(all_ids)] if all_ids else None,
        "spot_checked": len(spot),
        "resolved": resolved,
        "resolve_rate": round(resolved / len(spot), 4) if spot else None,
    }


def score_stats(name):
    res = load_json(name, "gepa_result.json")
    tr = res["full_program_trace"]
    parent = [s for e in tr for s in e["subsample_scores"]]
    child = [s for e in tr for s in e["new_subsample_scores"]]
    deltas = [c - p for e in tr for p, c in zip(e["subsample_scores"], e["new_subsample_scores"])]
    batch_margins = [sum(e["new_subsample_scores"]) - sum(e["subsample_scores"]) for e in tr]
    return {
        "parent_per_example": dist(parent),
        "child_per_example": dist(child),
        "child_minus_parent_per_example": dist(deltas),
        "per_batch_sum_margin": dist(batch_margins),
    }


def main():
    out = {"HF_DATASETS_OFFLINE": os.environ.get("HF_DATASETS_OFFLINE")}

    out["1b_census"] = {
        "necrosis": census_run("necrosis"),
        "necrosis_dry": census_run("necrosis_dry"),
        "capture_GATE1": {"n_events": 3, "note": "message-only capture (reflect_{1,2,3}.json = [{role,content}]); no trace/ids/scores"},
    }
    out["1c_pairability_necrosis"] = pairability("necrosis")
    out["1c_pairability_necrosis_dry"] = pairability("necrosis_dry")
    out["1d_id_resolve_necrosis"] = id_resolve("necrosis")
    out["1e_score_stats_necrosis"] = score_stats("necrosis")
    # pooled == necrosis (single powered run); dry reported separately for completeness
    out["1e_score_stats_necrosis_dry"] = score_stats("necrosis_dry")

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
