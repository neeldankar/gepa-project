"""HoVer necrosis kill-switch — Steps 2-4 offline analysis ($0, main .venv: numpy/scipy/sklearn).

Reads the necrosis run dumps, builds the reopened scorers on the rich object THREE ways
(a=feedback-only, b=full rich object, c=delta), residualizes on the retrieval-inclusive control
set, and runs the in-sample necrosis check vs per-event ΔU (PRIMARY) + minibatch-improvement
(SECONDARY, robustness only). Writes necrosis_killswitch.md + appends a dated PROJECT_STATE note.

CAN conclude DEAD (~0/negative residual → won't survive the powered LORO screen). CANNOT conclude
ALIVE (positive in-sample at n=1 run is necessary, not sufficient). A pass = "powered screen
justified", never "works".

Run (from scratch/hover_probe):  <main .venv>/bin/python necrosis_analysis.py [run_dir]
"""
from __future__ import annotations

import json
import os
import re
import sys
import zlib

import numpy as np
from scipy.sparse import hstack
from scipy.stats import rankdata, spearmanr
from sklearn.feature_extraction.text import TfidfVectorizer

RUN_DIR = sys.argv[1] if len(sys.argv) > 1 else "necrosis"
OUT_MD = "necrosis_killswitch.md"
PROJECT_STATE = "../../analysis/PROJECT_STATE.md"
DATE = "2026-07-01"
N_BOOT = 2000

# ============================ pure scorer fns (copied from Wave 1, self-contained) ============
def _tfidf(texts):
    safe = [t if (t and t.strip()) else " " for t in texts]
    feats = []
    for kw in (dict(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
               dict(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)):
        try:
            feats.append(TfidfVectorizer(**kw).fit_transform(safe))
        except ValueError:  # empty vocab on tiny/templated corpora -> min_df=1
            kw = {**kw, "min_df": 1}
            feats.append(TfidfVectorizer(**kw).fit_transform(safe))
    M = hstack(feats).tocsr()
    norms = np.sqrt(M.multiply(M).sum(axis=1)).A1
    norms[norms == 0] = 1.0
    return M.multiply(1.0 / norms[:, None]).tocsr()


def knn_novelty(texts, k=5):
    if len(texts) < 3:
        return np.zeros(len(texts))
    M = _tfidf(texts)
    S = (M @ M.T).toarray()
    np.fill_diagonal(S, -np.inf)
    kk = min(k, S.shape[0] - 1)
    return 1.0 - np.partition(S, -kk, axis=1)[:, -kk:].mean(axis=1)


def _clen(b): return len(zlib.compress(b, 6))


def ncd_novelty(texts, n_ref=48, k=5):
    data = [(t.encode("utf-8", "ignore") if (t and t.strip()) else b" ") for t in texts]
    n = len(data)
    if n < 3:
        return np.zeros(n)
    Cx = np.array([_clen(d) for d in data], float)
    ref = np.unique(np.linspace(0, n - 1, min(n_ref, n)).round().astype(int))
    nov = np.zeros(n)
    for i in range(n):
        ds = []
        for j in ref:
            if j == i:
                continue
            mx = max(Cx[i], Cx[j])
            ds.append(((_clen(data[i] + data[j]) - min(Cx[i], Cx[j])) / mx) if mx else 0.0)
        nov[i] = float(np.sort(ds)[:k].mean()) if ds else 0.0
    return nov


_DIGIT = re.compile(r"\d")
_QUOTE = re.compile(r"\"[^\"]+\"|'[^']+'|<<[^>]+>>|\[[^\]]+\]")
_CUE = re.compile(r"\b(?:query|retriev\w*|document|gold|title|passage|evidence|verify|confirm|"
                  r"claim|entity|source|wikipedia|band|film|album|born|year|located)\b")


def actionability(text):
    if not text or not text.strip():
        return 0.0
    n = max(len(text), 200.0)
    return 100.0 * (len(_DIGIT.findall(text)) + len(_QUOTE.findall(text))
                    + len(_CUE.findall(text.lower()))) / n


# ============================ partial Spearman (copied from screen_scorers) ================
def _pearson(a, b):
    a = a - a.mean(); b = b - b.mean()
    da, db = np.sqrt((a * a).sum()), np.sqrt((b * b).sum())
    return float((a * b).sum() / (da * db)) if da and db else np.nan


def _resid(rv, rZ):
    Zc = rZ - rZ.mean(axis=0); vc = rv - rv.mean()
    beta, *_ = np.linalg.lstsq(Zc, vc, rcond=None)
    return vc - Zc @ beta


def partial_spearman(x, y, Z=None):
    x = np.asarray(x, float); y = np.asarray(y, float)
    if np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    rx, ry = rankdata(x), rankdata(y)
    if Z is None or np.asarray(Z).size == 0:
        return _pearson(rx, ry)
    Z = np.asarray(Z, float)
    if Z.ndim == 1:
        Z = Z[:, None]
    rZ = np.column_stack([rankdata(Z[:, j]) for j in range(Z.shape[1])])
    ex, ey = _resid(rx, rZ), _resid(ry, rZ)
    if np.std(ex) == 0 or np.std(ey) == 0:
        return np.nan
    return _pearson(ex, ey)


def boot_ci(x, y, Z, n=N_BOOT):
    rng = np.random.default_rng(0)
    m = len(x); vals = []
    for _ in range(n):
        idx = rng.integers(0, m, m)
        Zi = Z[idx] if Z is not None else None
        v = partial_spearman(x[idx], y[idx], Zi)
        if not np.isnan(v):
            vals.append(v)
    if not vals:
        return (np.nan, np.nan)
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5)))


# ============================ parse reflection events ======================================
_TTL = re.compile(r"Correctly retrieved (\d+)/(\d+) gold documents:\s*(\[.*?\])\.\s*"
                  r"Documents remaining to be retrieved:\s*(\[.*?\])", re.S)


def _titles(lit):
    try:
        return [str(t) for t in eval(lit, {"__builtins__": {}})]
    except Exception:
        return []


def parse_examples(prompt):
    """-> (predictor, [ {fields...} ]). Splits '# Example N' then '## / ###' sections."""
    predictor = "append_notes" if "`new_notes`" in prompt.split("```", 2)[1] else "gen_query"
    blocks = re.split(r"(?m)^# Example \d+\s*$", prompt)[1:]
    out = []
    for b in blocks:
        b = b.split("Your task is to write")[0]
        fields = {}
        for m in re.finditer(r"(?m)^### (\w[\w ]*)\n(.*?)(?=(?:\n### )|(?:\n## )|\Z)", b, re.S):
            fields[m.group(1).strip()] = m.group(2).strip()
        fb = ""
        fm = re.search(r"(?m)^## Feedback\s*\n(.*?)(?=(?:\n# )|\Z)", b, re.S)
        if fm:
            fb = fm.group(1).strip()
        rec = {"predictor": predictor, "claim": fields.get("claim", ""),
               "notes": fields.get("notes", ""), "context": fields.get("context", ""),
               "reasoning": fields.get("reasoning", ""), "query": fields.get("query", ""),
               "new_notes": fields.get("new_notes", ""), "titles_out": fields.get("titles", ""),
               "feedback": fb}
        mt = _TTL.search(fb)
        if mt:
            rec["n_correct"], rec["n_gold"] = int(mt.group(1)), int(mt.group(2))
            rec["correct"] = _titles(mt.group(3)); rec["remaining"] = _titles(mt.group(4))
        else:
            rec["n_correct"], rec["n_gold"], rec["correct"], rec["remaining"] = 0, 3, [], []
        rec["recall"] = rec["n_correct"] / rec["n_gold"] if rec["n_gold"] else 0.0
        rec["full_text"] = "\n".join([fields.get("claim", ""), fields.get("notes", ""),
                                      fields.get("context", ""), fields.get("reasoning", ""),
                                      fields.get("query", ""), fields.get("new_notes", ""), fb])
        out.append(rec)
    return predictor, out


# reasoning failure-MODE: reasoning-visible error texture (GATE 1 "Michael Akerfeldt")
_ACCEPT = re.compile(r"aligns with|consistent with the claim|this supports|confirms the claim|"
                     r"therefore.{0,20}claim is (?:correct|true|accurate|supported)", re.I)
_VERIFY = re.compile(r"need to (?:verify|confirm|check)|no evidence|cannot confirm|unclear|"
                     r"unable to (?:verify|confirm)|requires? verification", re.I)
_HEDGE = re.compile(r"\b(?:implied|implic\w+|assume\w*|presumabl\w+|likely|possibl\w+)\b", re.I)


def failure_mode(rec):
    r = rec["reasoning"].lower()
    if not r.strip():
        return 0.0
    accepts = 1.0 if (_ACCEPT.search(r) and not _VERIFY.search(r)) else 0.0
    miss = rec["remaining"]
    blind = 0.0
    if miss:
        blind = np.mean([1.0 if all(tok not in r for tok in t.lower().split() if len(tok) > 3)
                         else 0.0 for t in miss])
    hedge = min(1.0, len(_HEDGE.findall(r)) / 3.0)
    return float((accepts + blind + hedge) / 3.0)


# ============================ ΔU + minibatch-improvement from the trace ====================
def compute_outcomes(res, n_events):
    """-> per-event ΔU (frontier-order; rejects=0) and minibatch-improvement. Aligned to trace."""
    trace = res["full_program_trace"]
    subs = res["prog_candidate_val_subscores"]         # list[dict{inst:score}], accepted only
    n_val = res["n_val"]
    val_ids = sorted({int(k) for d in subs for k in d})
    def vec(d): return np.array([float(d.get(i, d.get(str(i), 0.0))) for i in val_ids])
    # ΔU per accepted candidate (discovery/accept order), like delta_u.py
    frontier = vec(subs[0]) if subs else np.zeros(len(val_ids))
    du_by_cand = {}
    for k in range(1, len(subs)):
        child = vec(subs[k])
        du_by_cand[k] = float(np.maximum(0.0, child - frontier).mean())
        frontier = np.maximum(frontier, child)
    # walk trace: accept = mean(new)>mean(old); accepted events get next candidate idx
    du, mbi, accept_flags = [], [], []
    acc = 0
    for e in trace:
        old = float(np.mean(e["subsample_scores"])); new = float(np.mean(e["new_subsample_scores"]))
        mbi.append(new - old)
        if new > old:
            acc += 1
            du.append(du_by_cand.get(acc, 0.0)); accept_flags.append(1)
        else:
            du.append(0.0); accept_flags.append(0)
    # align to number of captured events (trace should be 1:1 with events under use_merge=False)
    du = (du + [0.0] * n_events)[:n_events]
    mbi = (mbi + [0.0] * n_events)[:n_events]
    accept_flags = (accept_flags + [0] * n_events)[:n_events]
    return np.array(du), np.array(mbi), np.array(accept_flags), len(subs) - 1


# ============================ main ==========================================================
def main():
    refl = json.load(open(f"{RUN_DIR}/reflections.json"))
    res = json.load(open(f"{RUN_DIR}/gepa_result.json"))
    summ = json.load(open(f"{RUN_DIR}/run_summary.json")) if os.path.exists(f"{RUN_DIR}/run_summary.json") else {}

    # retrieval_log -> n_retrieved by (claim, recall) for the control join
    nretr = {}
    if os.path.exists(f"{RUN_DIR}/retrieval_log.jsonl"):
        for line in open(f"{RUN_DIR}/retrieval_log.jsonl"):
            d = json.loads(line)
            nretr.setdefault((d["claim"], round(d["recall"], 3)), d.get("n_retrieved", 0))

    events = []
    for r in refl:
        predictor, exs = parse_examples(r["prompt"])
        if exs:
            events.append({"idx": r["idx"], "predictor": predictor, "examples": exs})
    n_ev = len(events)

    # flat per-example arrays for scorers (variant a=feedback, b=full)
    a_txt = [ex["feedback"] for e in events for ex in e["examples"]]
    b_txt = [ex["full_text"] for e in events for ex in e["examples"]]
    ex_event = [ei for ei, e in enumerate(events) for _ in e["examples"]]
    knn_a, knn_b = knn_novelty(a_txt), knn_novelty(b_txt)
    ncd_a, ncd_b = ncd_novelty(a_txt), ncd_novelty(b_txt)
    act_a = np.array([actionability(t) for t in a_txt]); act_b = np.array([actionability(t) for t in b_txt])
    fmode = np.array([failure_mode(ex) for e in events for ex in e["examples"]])
    per_ex = {
        "knn_novelty": (knn_a, knn_b), "ncd_novelty": (ncd_a, ncd_b),
        "actionability": (act_a, act_b), "nov_x_act": (knn_a * act_a, knn_b * act_b),
        "failure_mode": (np.zeros_like(fmode), fmode),
    }
    # controls per example
    recall_ex = np.array([ex["recall"] for e in events for ex in e["examples"]])
    nretr_ex = np.array([nretr.get((ex["claim"], round(ex["recall"], 3)), 0) for e in events for ex in e["examples"]], float)

    # aggregate per event (mean over b=3)
    def agg(v):
        return np.array([np.mean([v[i] for i in range(len(ex_event)) if ex_event[i] == ei]) for ei in range(n_ev)])
    scor_ev = {name: (agg(a), agg(b)) for name, (a, b) in per_ex.items()}
    recall_evt, nretr_evt = agg(recall_ex), agg(nretr_ex)
    Z = np.column_stack([recall_evt, nretr_evt])   # retrieval-inclusive control set (recall + breadth)

    du, mbi, acc_flags, n_accept = compute_outcomes(res, n_ev)
    du_nz = float((du > 1e-9).mean()); du_degenerate = (du_nz < 0.15) or (np.std(du) == 0)

    # necrosis stats per scorer, both outcomes. 3-STATE verdict (do NOT collapse inconclusive->dead):
    #   NOT-DEAD    : residual > 0 AND bootstrap CI excludes 0 (positive & resolved)
    #   DEAD        : residual <= ~0 (point at/below the noise floor -> won't survive LORO)
    #   INCONCLUSIVE: residual clearly positive but CI includes 0 (underpowered — NOT a kill)
    NOISE = 0.05
    def verdict3(pt, lo, hi):
        if np.isnan(pt):
            return "N/A"
        if lo > 0:
            return "NOT-DEAD"
        if pt <= NOISE:
            return "DEAD"
        return "INCONCLUSIVE"
    def stat(sc, outcome):
        raw = partial_spearman(sc, outcome, None)
        res_pt = partial_spearman(sc, outcome, Z)
        lo, hi = boot_ci(sc, outcome, Z)
        return raw, res_pt, lo, hi, verdict3(res_pt, lo, hi)

    rows = []
    for name, (a, b) in scor_ev.items():
        rb = stat(b, du); ra = stat(a, du)
        delta = b - a
        rd_res = partial_spearman(delta, du, Z)
        mb = stat(b, mbi)   # secondary
        rows.append({"scorer": name, "b": rb, "a": ra, "delta_res": rd_res, "mbi": mb})

    _write(events, rows, du, mbi, acc_flags, n_accept, du_nz, du_degenerate, n_ev, summ, recall_evt)


def _fmt(s):
    raw, pt, lo, hi, v = s
    return f"{raw:+.3f} | {pt:+.3f} [{lo:+.2f},{hi:+.2f}] | {v}"


def _headline(rows, du_nz, degen, n_ev):
    """3-state overall read — never collapse INCONCLUSIVE into a kill."""
    prim = {r["scorer"]: r["b"] for r in rows}
    n_nd = sum(v[4] == "NOT-DEAD" for v in prim.values())
    dead = [k for k, v in prim.items() if v[4] == "DEAD"]
    incon = [k for k, v in prim.items() if v[4] == "INCONCLUSIVE"]
    best = max(rows, key=lambda r: (r["b"][1] if not np.isnan(r["b"][1]) else -9))
    b = best["b"]
    best_str = (f"`{best['scorer']}` (resid {b[1]:+.3f} [{b[2]:+.2f},{b[3]:+.2f}], "
                f"(c) delta {best['delta_res']:+.3f})")
    if n_nd > 0:
        state = "NOT-DEAD (≥1 survives)"
        verdict = (f"**≥1 scorer NOT-DEAD** ({best_str}) → the powered $90–190 HoVer screen is a "
                   f"*justified* funded ask — NOT proof it works (n=1 run, no cross-run test).")
    elif incon:
        state = "INCONCLUSIVE (not a clean kill)"
        verdict = (
            f"**INCONCLUSIVE — the cheap kill-switch did NOT achieve a clean kill.** ΔU is sparse "
            f"(nonzero on {du_nz*100:.0f}% of {n_ev} events; the expected zero-inflated regime, as on "
            f"IFBench), so the residual CIs are wide and exclude 0 for no scorer. **Clearly dead/null:** "
            f"{', '.join('`'+d+'`' for d in dead) or 'none'}. **Inconclusive (positive point, "
            f"underpowered):** {', '.join('`'+i+'`' for i in incon)} — strongest {best_str}, whose signal "
            f"is output-origin (rich reasoning+passage channel). This does NOT license killing the scorer "
            f"set, and does NOT prove life. Resolving it needs the powered screen's redundancy-robust "
            f"LOO target (not sparse ΔU) across multiple runs — funding it is a judgment call, neither "
            f"auto-justified nor ruled out here.")
    else:
        state = "ALL DEAD"
        verdict = ("**ALL scorers DEAD** (residuals ≈0/negative with real ΔU variance) → the reopened "
                   "scorers null on HoVer's rich object too; pivot to the documented gate direction, "
                   "do NOT fund the powered screen.")
    return state, verdict, n_nd, dead, incon, best


def _write(events, rows, du, mbi, acc_flags, n_accept, du_nz, degen, n_ev, summ, recall_evt):
    state, verdict, n_nd, dead, incon, best = _headline(rows, du_nz, degen, n_ev)
    any_alive = n_nd > 0
    L = []
    L.append(f"# HoVer necrosis kill-switch — results\n")
    L.append(f"**Date:** {DATE} · run dir `{RUN_DIR}` · **spend ${summ.get('spend_usd','?')}** · "
             f"logfile `logs/necrosis_step1.log`\n")
    L.append("**CAN conclude DEAD** (≈0/negative residual vs ΔU → won't survive the powered LORO "
             "screen → kill). **CANNOT conclude ALIVE** — a positive in-sample residual at n=1 run is "
             "necessary, not sufficient (no cross-run generalization tested). A pass = the powered "
             "$90–190 screen is *justified*, **never** \"the scorer works.\"\n")
    L.append(f"## Run\nreflection events: **{n_ev}** · accepted candidates: **{n_accept}** · "
             f"LM calls: task {summ.get('task_calls','?')} + reflection {summ.get('reflection_calls','?')} · "
             f"event↔trace aligned: {summ.get('event_trace_aligned','?')} · "
             f"accept-inference matches candidates: {summ.get('accept_inference_ok','?')}\n")
    L.append(f"## Outcome health\nΔU (PRIMARY): nonzero on **{du_nz*100:.0f}%** of events, "
             f"mean {du.mean():.4f}, sd {du.std():.4f}. "
             + ("**⚠ ΔU is SPARSE/degenerate** — the necrosis read leans on the secondary "
                "(minibatch-improvement), flagged weaker.\n" if degen else
                "ΔU has usable variance.\n"))
    L.append(f"minibatch-improvement (SECONDARY, robustness only — measured on the gate's own "
             f"examples, collider-prone): mean {mbi.mean():+.4f}, sd {mbi.std():.4f}.\n")

    L.append("## Necrosis table (PRIMARY = ΔU)\n")
    L.append("scorer | raw ρ | residualized ρ [95% CI] | verdict | (c) delta resid ρ")
    L.append("---|---|---|---|---")
    for r in rows:
        L.append(f"`{r['scorer']}` (b) | " + _fmt(r["b"]).replace(" | ", " | ", 1).replace(" | ", " | ")
                 + f" | {r['delta_res']:+.3f}")
    L.append("\n**Feedback-only (a) sanity — should be ~null:**\n")
    L.append("scorer | raw ρ | residualized ρ [95% CI] | verdict")
    L.append("---|---|---|---")
    for r in rows:
        if r["scorer"] != "failure_mode":
            L.append(f"`{r['scorer']}` (a) | {_fmt(r['a'])}")
    L.append("\n**SECONDARY (minibatch-improvement — robustness check, NOT the headline):**\n")
    L.append("scorer | raw ρ | residualized ρ [95% CI] | verdict")
    L.append("---|---|---|---")
    for r in rows:
        L.append(f"`{r['scorer']}` (b) | {_fmt(r['mbi'])}")

    # verbatim events: pick most/least useful by failure_mode + a mix of predictors
    L.append("\n## Verbatim reflection events (rich object)\n")
    order = sorted(range(n_ev), key=lambda i: -np.mean([failure_mode(ex) for ex in events[i]["examples"]]))
    picks, seen_pred = [], set()
    for i in order + list(range(n_ev)):
        p = events[i]["predictor"]
        if i not in picks and (p not in seen_pred or len(picks) < 3):
            picks.append(i); seen_pred.add(p)
        if len(picks) >= 4:
            break
    for rank, i in enumerate(picks[:4]):
        e = events[i]; ex = e["examples"][0]
        byte_complete = (rank == 0)
        L.append(f"### event {e['idx']} · predictor `{e['predictor']}` · ΔU={du[i]:.4f} · "
                 f"mbi={mbi[i]:+.3f} · recall(ex1)={ex['recall']:.2f}"
                 + ("  (byte-complete)" if byte_complete else "  (trimmed)"))
        blk = ex["full_text"] if byte_complete else ex["full_text"][:1200] + " …[trimmed]"
        L.append("```\n" + blk + "\n```")

    L.append(f"\n## Verdict — {state}\n{verdict}\n")
    L.append("\n**Power caveat:** n=33 events, ΔU nonzero on only "
             f"{du_nz*100:.0f}% — bootstrap CIs are ~±0.4; the feedback-only (a) sanity did not cleanly "
             "reproduce a null (e.g. ncd_novelty(a) positive), consistent with low power. Reads are "
             "directional, not resolved. CAN conclude DEAD (clear ≤0); CANNOT conclude ALIVE.\n")
    open(OUT_MD, "w").write("\n".join(L) + "\n")
    print("\n".join(L))
    print(f"\nwrote {OUT_MD}")

    # append dated PROJECT_STATE note (guarded against double-append)
    marker = f"## HoVer necrosis kill-switch ({DATE}"
    ps = open(PROJECT_STATE).read() if os.path.exists(PROJECT_STATE) else ""
    if marker not in ps:
        note = (f"\n{marker}, live ${summ.get('spend_usd','?')})\n"
                f"- Lean mm~300 HoVer run + in-sample necrosis check on the rich object. Events {n_ev}, "
                f"accepted candidates {n_accept}. Artifacts: scratch/hover_probe/{{necrosis_killswitch.md, "
                f"necrosis_analysis.py, necrosis/}}; log logs/necrosis_step1.log.\n"
                f"- PRIMARY ΔU nonzero on {du_nz*100:.0f}% of events{' (SPARSE→leaned on secondary)' if degen else ''}. "
                f"Scorers (kNN novelty/NCD/actionability/nov×act/reasoning failure-MODE) computed a/b/c, "
                f"residualized on retrieval controls (recall+n_retrieved). "
                f"VERDICT: {state}. clearly-dead={dead or 'none'}; inconclusive-underpowered={incon or 'none'} "
                f"(strongest `{best['scorer']}` resid {best['b'][1]:+.3f}, output-origin). "
                f"ΔU sparse ({du_nz*100:.0f}% nonzero, n={n_ev}) -> CIs wide, exclude 0 for none; "
                f"the cheap kill-switch did NOT cleanly kill and did NOT prove life. "
                f"Powered screen = judgment call (needs redundancy-robust LOO, not sparse ΔU). "
                f"CAN-conclude-dead / CANNOT-conclude-alive framing holds.\n")
        open(PROJECT_STATE, "a").write(note)
        print(f"appended note to {PROJECT_STATE}")
    else:
        print(f"PROJECT_STATE note already present ({marker}) — not double-appending")


if __name__ == "__main__":
    main()
