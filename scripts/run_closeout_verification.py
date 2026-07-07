"""Closeout verification — two review holes ($0, read-only, no runs).

STEP 1 (done outside): gen_query IS optimized (6 distinct instr across 11 necrosis candidates) -> H2 LIVE.
STEP 2  : OUTCOME ICC (ΔU + LOO) by example + bootstrap CI  -> replaces R²=0.087 as the closing stat.
STEP 2b : hurdle split (logistic accept / OLS ΔU|accept) + top-decile enrichment.
STEP 3  : HoVer accepted-candidate gen_query diff + per-candidate valset recall trajectory.
STEP 4  : retrieval-fixability prevalence on the 33 HoVer events.

Run: HF_DATASETS_OFFLINE=1 .venv/bin/python scripts/run_closeout_verification.py
"""
from __future__ import annotations

import json
import re
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import roc_auc_score

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.screen_scorers import batch_frame, KEYS, aggregate_events
from gepa_si.screen.scorer_inputs import constraint_type, tractability_of
from gepa_si.screen.scorers_semantic import build_semantic_matrix

warnings.filterwarnings("ignore")
NECRO = "scratch/hover_probe/necrosis"
rng = np.random.default_rng(0)


def icc1(values, groups):
    df = pd.DataFrame({"v": values, "g": groups}).dropna()
    grand = df.v.mean(); gs = df.groupby("g").v
    ni = gs.size().to_numpy(); k = len(ni); n = len(df)
    if k < 2 or n <= k:
        return np.nan
    ssb = float((ni * (gs.mean().to_numpy() - grand) ** 2).sum()); msb = ssb / (k - 1)
    ssw = float(sum(((v - v.mean()) ** 2).sum() for _, v in gs)); msw = ssw / (n - k)
    k0 = (n - (ni ** 2).sum() / n) / (k - 1)
    den = msb + (k0 - 1) * msw
    return float((msb - msw) / den) if den > 0 else np.nan


def icc_boot(values, groups, nboot=1000):
    values = np.asarray(values); groups = np.asarray(groups)
    uniq = np.unique(groups)
    by = {g: values[groups == g] for g in uniq}
    pt = icc1(values, groups); boots = []
    for _ in range(nboot):
        samp = rng.choice(uniq, size=len(uniq), replace=True)
        vv, gg = [], []
        for j, g in enumerate(samp):
            vv.append(by[g]); gg.append(np.full(len(by[g]), j))
        v = icc1(np.concatenate(vv), np.concatenate(gg))
        if not np.isnan(v):
            boots.append(v)
    lo, hi = (np.percentile(boots, [2.5, 97.5]) if boots else (np.nan, np.nan))
    return pt, float(lo), float(hi)


# ============================ IFBench: build batch frame + example attribution ============
runs = load_corpus()
bf = batch_frame(runs)
b3 = bf[bf.b == 3].copy()
# expand batch outcome to example slots (via minibatch_ids -> trainset id)
rows = []
for r in [x for x in runs if x.b == 3]:
    loo_map = dict(zip(zip([r.seed] * len(r.cycles), [c.iteration for c in r.cycles]),
                       [None] * len(r.cycles)))
    bsub = b3[b3.seed == r.seed].set_index("iteration")
    for c in r.cycles:
        if c.iteration not in bsub.index:
            continue
        loo = float(bsub.loc[c.iteration, "loo_contribution"]); du = float(bsub.loc[c.iteration, "delta_u"])
        for tid in c.minibatch_ids:
            rows.append({"trainset_id": tid, "loo": loo, "delta_u": du})
slots = pd.DataFrame(rows)

print("=" * 74 + "\nSTEP 2 — OUTCOME ICC (replaces R²=0.087)\n" + "=" * 74)
print(f"IFBench: {len(slots)} example-slots over {slots.trainset_id.nunique()} examples")
for out in ["delta_u", "loo"]:
    pt, lo, hi = icc_boot(slots[out].to_numpy(), slots.trainset_id.to_numpy())
    print(f"  outcome={out:8} ICC(1)={pt:+.3f}  95% CI [{lo:+.3f}, {hi:+.3f}]  "
          f"-> {'target EXISTS' if lo > 0.05 else 'between-example ~0: CLOSED WITH PREJUDICE'}")

# HoVer outcome ICC (thin): per-event ΔU + mbi grouped by claim
res = json.load(open(f"{NECRO}/gepa_result.json")); refl = json.load(open(f"{NECRO}/reflections.json"))
trace = res["full_program_trace"]; subs = res["prog_candidate_val_subscores"]
val_ids = sorted({int(k) for d in subs for k in d})
def vec(d): return np.array([float(d.get(str(i), d.get(i, 0.0))) for i in val_ids])
front = vec(subs[0]).copy(); du_c = {}
for k in range(1, len(subs)):
    ch = vec(subs[k]); du_c[k] = float(np.maximum(0, ch - front).mean()); front = np.maximum(front, ch)
acc = 0; ev_du = []; ev_mbi = []
for t in trace:
    old = np.mean(t["subsample_scores"]); new = np.mean(t["new_subsample_scores"]); ev_mbi.append(new - old)
    if new > old:
        acc += 1; ev_du.append(du_c.get(acc, 0.0))
    else:
        ev_du.append(0.0)
def claim0(p):
    b = re.split(r"(?m)^# Example \d+\s*$", p)[1]
    m = re.search(r"(?m)^### claim\n(.*)", b)
    return m.group(1)[:60] if m else ""
hov_claim = [claim0(r["prompt"]) for r in refl]
print(f"  HoVer (33 ev, {len(set(hov_claim))} claims, THIN): "
      f"ICC(ΔU)={icc1(np.array(ev_du), np.array(hov_claim)):+.3f}  "
      f"ICC(mbi)={icc1(np.array(ev_mbi), np.array(hov_claim)):+.3f}")

# ============================ STEP 2b — hurdle + top-decile ============================
print("\n" + "=" * 74 + "\nSTEP 2b — hurdle split + top-decile enrichment\n" + "=" * 74)
sem = build_semantic_matrix(runs); semb3 = sem[sem.b == 3]
ctract = {(s, it, p): float(sum(tractability_of(f) for f in c.failed_ids_per_example[p]))
          for r in runs if r.b == 3 for c in r.cycles for p, _ in enumerate(c.minibatch_ids) for s, it in [(r.seed, c.iteration)]}
agg_ct = aggregate_events(semb3.assign(constraint_tractability=[ctract.get((s, it, p), np.nan) for s, it, p in zip(semb3.seed, semb3.iteration, semb3.example_pos)]), ["constraint_tractability"])[KEYS + ["constraint_tractability_mean"]]
m = b3.merge(agg_ct, on=KEYS, how="left")
alltypes = sorted({constraint_type(f) for ids in m.failed_ids for f in ids})
for t in alltypes:
    m[f"ct_{t}"] = m.failed_ids.apply(lambda ids: (sum(constraint_type(f) == t for f in ids) / len(ids)) if ids else 0.0)
tcols = [f"ct_{t}" for t in alltypes if int((m[f"ct_{t}"] > 0).sum()) >= 5]
CONTROLS = ["difficulty", "n2_peakedness", "parent_dpareto", "iteration", "constraint_tractability_mean"] + tcols
sub = m.dropna(subset=CONTROLS + ["loo_contribution", "delta_u", "accept"])
X = sub[CONTROLS].to_numpy()
# hurdle (i): logistic accept
clf = LogisticRegression(max_iter=1000).fit(X, sub.accept.astype(int))
auc = roc_auc_score(sub.accept.astype(int), clf.predict_proba(X)[:, 1])
# hurdle (ii): OLS ΔU | accept
acc_sub = sub[sub.accept]
Xa = acc_sub[CONTROLS].to_numpy(); ya = acc_sub.delta_u.to_numpy()
lm = LinearRegression().fit(Xa, ya); r2a = 1 - ((ya - lm.predict(Xa)) ** 2).sum() / ((ya - ya.mean()) ** 2).sum()
print(f"  hurdle (i)  P(accept) ~ 20 controls : AUC={auc:.3f}  (base accept={sub.accept.mean():.2f})")
print(f"  hurdle (ii) ΔU|accept ~ 20 controls : R²={r2a:+.3f}  (n_accept={len(acc_sub)})")
# top-decile enrichment on LOO
sub = sub.merge(aggregate_events(semb3, ["knn_novelty_b", "actionability_b", "failure_mode"]), on=KEYS, how="left")
thr = sub.loo_contribution.quantile(0.9)
top = sub[sub.loo_contribution >= thr]; rest = sub[sub.loo_contribution < thr]
print(f"  top-decile enrichment (LOO>=q90={thr:.4f}, n_top={len(top)}):")
for f in ["constraint_tractability_mean", "difficulty", "knn_novelty_b_mean", "actionability_b_mean", "failure_mode_mean"]:
    if f in sub:
        print(f"    {f:32} top={top[f].mean():+.3f} vs rest={rest[f].mean():+.3f}  Δ={top[f].mean()-rest[f].mean():+.3f}")

# ============================ STEP 3 — HoVer gen_query diff + recall trajectory ============
print("\n" + "=" * 74 + "\nSTEP 3 — HoVer accepted-candidate gen_query diff + recall trajectory\n" + "=" * 74)
cands = res["program_candidates"]; parents = res["parent_program_for_candidate"]
recall_traj = [float(np.mean(list(map(float, subs[k].values())))) for k in range(len(subs))]
print(f"  per-candidate valset recall trajectory (cand0->): {[round(x,3) for x in recall_traj]}")
print(f"  seed recall={recall_traj[0]:.3f}  best={max(recall_traj):.3f} (cand {int(np.argmax(recall_traj))})")
gq_edits = 0
for k in range(1, len(cands)):
    par = parents[k][0] if parents[k] else None
    if par is None:
        continue
    if cands[k].get("gen_query.predict") != cands[par].get("gen_query.predict"):
        gq_edits += 1
        if gq_edits <= 2:
            print(f"\n  ACCEPTED edit touching gen_query: cand {par}->{k}")
            print(f"    parent gen_query[:200]: {cands[par].get('gen_query.predict','')[:200]!r}")
            print(f"    child  gen_query[:200]: {cands[k].get('gen_query.predict','')[:200]!r}")
print(f"\n  accepted candidates whose gen_query instruction changed vs parent: {gq_edits}/{len(cands)-1}")

# ============================ STEP 4 — retrieval-fixability prevalence ============================
print("\n" + "=" * 74 + "\nSTEP 4 — retrieval-fixability prevalence (33 HoVer events)\n" + "=" * 74)
retr = [json.loads(l) for l in open(f"{NECRO}/retrieval_log.jsonl")]
# map claim(first90)->retrieval row (first occurrence)
retr_by_claim = {}
for d in retr:
    retr_by_claim.setdefault(d["claim"][:60], d)
def ex0_fields(prompt):
    b = re.split(r"(?m)^# Example \d+\s*$", prompt)[1].split("Your task is to write")[0]
    f = {}
    for mm in re.finditer(r"(?m)^### (\w[\w ]*)\n(.*?)(?=(?:\n### )|(?:\n## )|\Z)", b, re.S):
        f[mm.group(1).strip()] = mm.group(2).strip()
    fb = re.search(r"(?m)^## Feedback\s*\n(.*?)(?=(?:\n# )|\Z)", b, re.S)
    rem = re.search(r"remaining to be retrieved:\s*(\[.*?\])", fb.group(1) if fb else "")
    try:
        missed = eval(rem.group(1), {"__builtins__": {}}) if rem else []
    except Exception:
        missed = []
    return f, [str(x) for x in missed]

n_fail = n_sig = 0; matches = []
for r in refl:
    f, missed = ex0_fields(r["prompt"])
    if not missed:
        continue
    n_fail += 1
    text = " ".join([f.get("claim", ""), f.get("notes", ""), f.get("reasoning", "")]).lower()
    d = retr_by_claim.get(f.get("claim", "")[:60])
    if not d:
        continue
    ret_titles = " ".join(t.lower() for t in d.get("retrieved", []))
    queries = " ".join(h.get("query", "").lower() for h in d.get("per_hop", []))
    for ent in missed:
        toks = [w for w in re.findall(r"[a-z0-9]+", ent.lower()) if len(w) > 3]
        named = any(w in text for w in toks)                     # entity named in reasoning/notes/claim
        not_retrieved = not any(w in ret_titles for w in toks)   # absent from retrieved titles
        not_in_query = not any(w in queries for w in toks)       # absent from generated queries
        if named and not_retrieved and not_in_query:
            n_sig += 1
            matches.append((r["idx"], ent, f.get("claim", "")[:70], queries[:120]))
            break
print(f"  failures (events w/ missed docs): {n_fail}")
print(f"  retrieval-fixability signature (entity NAMED in reasoning/notes, ABSENT from retrieved AND from queries): {n_sig}/{n_fail} ({n_sig/max(n_fail,1):.0%})")
print("  sample matches (event, missed-entity, claim, query):")
for idx, ent, claim, q in matches[:3]:
    print(f"    ev{idx}: '{ent}' | claim: {claim} | query: {q!r}")

print("\nDONE — $0 read-only, no runs.")
