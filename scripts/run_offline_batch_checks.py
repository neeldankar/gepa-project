"""Five $0 offline checks from external review (read-only, no LM/GEPA runs).

CHECK 1  ICC (between-example / total variance) per scorer            -> static vs overgen-filter
CHECK 2  control-block R2 on LOO + dU                                 -> id-absorbs vs global-unpredictable
CHECK 4  accept-rate by scorer (logistic + tercile), both corpora     -> collider/imputation-bias story
CHECK 5  batch TF-IDF dispersion vs outcome                           -> DPP/diversity precursor
(CHECK 3 = manual HoVer event classification, done in the report — not here.)

Run: HF_DATASETS_OFFLINE=1 /Users/neeldankar/Desktop/gepa-project/.venv/bin/python scripts/run_offline_batch_checks.py
"""
from __future__ import annotations

import json
import re
import warnings

import numpy as np
import pandas as pd
from scipy import stats
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import StandardScaler

from gepa_si.screen.corpus_io import load_corpus
from gepa_si.screen.scorers_semantic import build_semantic_matrix
from gepa_si.screen.screen_scorers import batch_frame, KEYS, aggregate_events
from gepa_si.screen.scorer_inputs import constraint_type
from gepa_si.screen.triples_io import extract_reflection_triples

warnings.filterwarnings("ignore")
NECRO = "scratch/hover_probe/necrosis"
SEM_B = ["knn_novelty_b", "ncd_novelty_b", "actionability_b", "nov_x_act_b", "failure_mode"]


# ----------------------------- helpers -----------------------------
def icc1(values, groups):
    """One-way random-effects ICC(1) = between-group share of variance."""
    df = pd.DataFrame({"v": values, "g": groups}).dropna()
    grand = df["v"].mean()
    gs = df.groupby("g")["v"]
    ni = gs.size().to_numpy()
    k = len(ni)
    n = len(df)
    if k < 2 or n <= k:
        return np.nan
    msb = (gs.mean().to_numpy() - grand) ** 2
    ssb = float((ni * msb).sum())
    msb = ssb / (k - 1)
    ssw = float(sum(((v - v.mean()) ** 2).sum() for _, v in gs))
    msw = ssw / (n - k)
    k0 = (n - (ni ** 2).sum() / n) / (k - 1)   # adjusted mean group size
    denom = msb + (k0 - 1) * msw
    return float((msb - msw) / denom) if denom > 0 else np.nan


def tfidf_matrix(texts):
    safe = [t if (t and t.strip()) else " " for t in texts]
    feats = []
    for kw in (dict(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
               dict(analyzer="char_wb", ngram_range=(3, 5), min_df=2, sublinear_tf=True)):
        try:
            feats.append(TfidfVectorizer(**kw).fit_transform(safe))
        except ValueError:
            feats.append(TfidfVectorizer(**{**kw, "min_df": 1}).fit_transform(safe))
    M = hstack(feats).tocsr()
    nrm = np.sqrt(M.multiply(M).sum(axis=1)).A1
    nrm[nrm == 0] = 1.0
    return M.multiply(1.0 / nrm[:, None]).tocsr()


def ols_r2(X, y):
    X = np.asarray(X, float); y = np.asarray(y, float)
    m = LinearRegression().fit(X, y)
    yh = m.predict(X)
    ss = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ((y - yh) ** 2).sum() / ss if ss > 0 else np.nan
    n, p = X.shape
    adj = 1 - (1 - r2) * (n - 1) / (n - p - 1) if n - p - 1 > 0 else np.nan
    return float(r2), float(adj)


def spearman(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    if np.std(x) == 0 or np.std(y) == 0:
        return np.nan, np.nan
    r = stats.spearmanr(x, y)
    return float(r.correlation), float(r.pvalue)


# ----------------------------- load IFBench -----------------------------
print("loading IFBench corpus...")
runs = load_corpus()
b3 = [r for r in runs if r.b == 3]
sem = build_semantic_matrix(runs)
sem_b3 = sem[sem.b == 3].copy()

# example identity + constraint_tractability per slot
tid, ctract = {}, {}
from gepa_si.screen.scorer_inputs import tractability_of
for r in b3:
    for c in r.cycles:
        for p, t in enumerate(c.minibatch_ids):
            tid[(r.seed, c.iteration, p)] = t
            ctract[(r.seed, c.iteration, p)] = float(sum(tractability_of(f) for f in c.failed_ids_per_example[p]))
sem_b3["trainset_id"] = [tid.get((s, it, p)) for s, it, p in zip(sem_b3.seed, sem_b3.iteration, sem_b3.example_pos)]
sem_b3["constraint_tractability"] = [ctract.get((s, it, p)) for s, it, p in zip(sem_b3.seed, sem_b3.iteration, sem_b3.example_pos)]

# ============================ CHECK 1: ICC ============================
print("\n" + "=" * 70 + "\nCHECK 1 — ICC (between-example / total variance)\n" + "=" * 70)
SC1 = SEM_B + ["constraint_tractability"]
print(f"IFBench: {len(sem_b3)} b3 slots over {sem_b3.trainset_id.nunique()} examples")
icc_if = {}
for s in SC1:
    icc_if[s] = icc1(sem_b3[s].to_numpy(), sem_b3["trainset_id"].to_numpy())
    print(f"  {s:26} ICC(1) = {icc_if[s]:+.3f}   -> {'STATIC-ok (majority between)' if icc_if[s]>0.5 else 'within-dominated -> favors overgen+filter'}")


# ----------------------------- load HoVer -----------------------------
def parse_hover_examples(prompt):
    predictor = "append_notes" if "`new_notes`" in prompt.split("```", 2)[1] else "gen_query"
    blocks = re.split(r"(?m)^# Example \d+\s*$", prompt)[1:]
    out = []
    for b in blocks:
        b = b.split("Your task is to write")[0]
        f = {}
        for m in re.finditer(r"(?m)^### (\w[\w ]*)\n(.*?)(?=(?:\n### )|(?:\n## )|\Z)", b, re.S):
            f[m.group(1).strip()] = m.group(2).strip()
        fb = ""
        fm = re.search(r"(?m)^## Feedback\s*\n(.*?)(?=(?:\n# )|\Z)", b, re.S)
        if fm:
            fb = fm.group(1).strip()
        mt = re.search(r"Correctly retrieved (\d+)/(\d+)", fb)
        rec = int(mt.group(1)) / int(mt.group(2)) if mt else 0.0
        full = "\n".join([f.get("claim", ""), f.get("notes", ""), f.get("context", ""),
                          f.get("reasoning", ""), f.get("query", ""), f.get("new_notes", ""), fb])
        out.append({"claim": f.get("claim", ""), "recall": rec, "full": full, "feedback": fb, "predictor": predictor})
    return out

refl = json.load(open(f"{NECRO}/reflections.json"))
res = json.load(open(f"{NECRO}/gepa_result.json"))
trace = res["full_program_trace"]
hov_events = [parse_hover_examples(r["prompt"]) for r in refl]
# per-event accept + outcomes
hov_acc = np.array([1 if np.mean(t["new_subsample_scores"]) > np.mean(t["subsample_scores"]) else 0 for t in trace])
# HoVer per-unit scorers (reuse build path lightly: knn/actionability on full texts)
from gepa_si.screen.scorers_semantic import knn_novelty, ncd_novelty, actionability
hov_full = [ex["full"] for e in hov_events for ex in e]
hov_claim = [ex["claim"] for e in hov_events for ex in e]
hov_knn = knn_novelty(hov_full)
hov_act = np.array([actionability(t) for t in hov_full])
print(f"\nHoVer: {len(hov_full)} units over {len(set(hov_claim))} claims (THIN — flag)")
print(f"  knn_novelty_b   ICC(1) = {icc1(hov_knn, hov_claim):+.3f}")
print(f"  actionability_b ICC(1) = {icc1(hov_act, hov_claim):+.3f}")

# ============================ CHECK 2: control-block R2 ============================
print("\n" + "=" * 70 + "\nCHECK 2 — control-block R2 on outcomes\n" + "=" * 70)
bf = batch_frame(runs)
merged = bf[bf.b == 3].copy()
agg_ct = aggregate_events(sem[sem.b == 3].assign(constraint_tractability=[  # per-batch tractability mean
    ctract.get((s, it, p), np.nan) for s, it, p in zip(sem[sem.b==3].seed, sem[sem.b==3].iteration, sem[sem.b==3].example_pos)])
    , ["constraint_tractability"])[KEYS + ["constraint_tractability_mean"]]
merged = merged.merge(agg_ct, on=KEYS, how="left")
all_types = sorted({constraint_type(f) for ids in merged["failed_ids"] for f in ids})
for t in all_types:
    merged[f"ct_{t}"] = merged["failed_ids"].apply(lambda ids: (sum(constraint_type(f)==t for f in ids)/len(ids)) if ids else 0.0)
type_cols = [f"ct_{t}" for t in all_types if int((merged[f"ct_{t}"]>0).sum()) >= 5]
CONTROLS20 = ["difficulty", "n2_peakedness", "parent_dpareto", "iteration", "constraint_tractability_mean"] + type_cols
sub = merged.dropna(subset=CONTROLS20 + ["loo_contribution", "delta_u"])
print(f"n={len(sub)} b3 batches; {len(CONTROLS20)} controls (4 diff + tractability + {len(type_cols)} ct_)")
X = sub[CONTROLS20].to_numpy()
for outcome in ["loo_contribution", "delta_u"]:
    y = sub[outcome].to_numpy()
    r2, adj = ols_r2(X, y)
    best = max(CONTROLS20, key=lambda c: (ols_r2(sub[[c]].to_numpy(), y)[0] or -9))
    br2 = ols_r2(sub[[best]].to_numpy(), y)[0]
    print(f"  {outcome:16} R2={r2:+.3f} adjR2={adj:+.3f} | nonzero-frac={np.mean(y>1e-9):.2f} | best single control={best} (R2={br2:+.3f})")

# ============================ CHECK 4: accept-rate by scorer ============================
print("\n" + "=" * 70 + "\nCHECK 4 — accept-rate by scorer\n" + "=" * 70)
# IFBench: per-batch mean scorer + accept. sem_batch = SEM_B means; constraint_tractability_mean
# already present on `merged` (from Check 2) — reuse it to avoid a column collision.
sem_batch = aggregate_events(sem[sem.b == 3], SEM_B)
ifb = merged.merge(sem_batch, on=KEYS, how="left")
scorer_cols = [(s, s + "_mean") for s in SEM_B] + [("constraint_tractability", "constraint_tractability_mean")]
print("IFBench (382 batches), accept ~ scorer (per-batch mean):")
print(f"  base accept rate = {ifb.accept.mean():.3f}")
for s, col in scorer_cols:
    d = ifb.dropna(subset=[col])
    x = d[col].to_numpy(); a = d.accept.astype(int).to_numpy()
    rho, p = spearman(x, a)
    # tercile accept rates
    q = pd.qcut(d[col].rank(method="first"), 3, labels=["lo","mid","hi"])
    rates = d.assign(q=q).groupby("q", observed=True).accept.mean()
    tag = "actionable" if s in ("actionability_b","nov_x_act_b") else ("failure_mode" if s=="failure_mode" else "")
    print(f"  {s:26} spearman(accept)={rho:+.3f} p={p:.3f}  terc[lo/mid/hi]={rates.get('lo',float('nan')):.2f}/{rates.get('mid',float('nan')):.2f}/{rates.get('hi',float('nan')):.2f}  {tag}")
# HoVer per-event mean scorer + accept (thin)
print("\nHoVer (33 events, accept rate=%.2f) accept ~ scorer (per-event mean):" % hov_acc.mean())
ev_knn = np.array([np.mean(hov_knn[i*3:(i+1)*3]) for i in range(len(hov_events))])
ev_act = np.array([np.mean(hov_act[i*3:(i+1)*3]) for i in range(len(hov_events))])
for nm, ev in [("knn_novelty_b", ev_knn), ("actionability_b", ev_act)]:
    rho, p = spearman(ev, hov_acc)
    print(f"  {nm:26} spearman(accept)={rho:+.3f} p={p:.3f} (THIN n=33)")

# ============================ CHECK 5: batch diversity ============================
print("\n" + "=" * 70 + "\nCHECK 5 — batch TF-IDF dispersion vs outcome\n" + "=" * 70)
# IFBench: per batch, 3 examples' full-triple tfidf -> mean pairwise cosine distance
tri_by_run = {r.seed: extract_reflection_triples(r) for r in b3}
rows = []
alltexts = []
idxmap = []
for r in b3:
    tri = tri_by_run[r.seed]
    for c in r.cycles:
        tl = tri.get(c.iteration, [])
        if len(tl) < 2:
            continue
        start = len(alltexts)
        for t in tl:
            alltexts.append(t.full())
        idxmap.append((r.seed, c.iteration, start, len(tl)))
M = tfidf_matrix(alltexts)
disp = {}
for seed, it, start, k in idxmap:
    rows_m = M[start:start+k]
    S = (rows_m @ rows_m.T).toarray()
    iu = np.triu_indices(k, 1)
    disp[(seed, it)] = float((1 - S[iu]).mean()) if len(iu[0]) else np.nan
merged["dispersion"] = [disp.get((s, it), np.nan) for s, it in zip(merged.seed, merged.iteration)]
d5 = merged.dropna(subset=["dispersion", "loo_contribution", "difficulty"]).merge(sem_batch, on=KEYS, how="left")
rho, p = spearman(d5["dispersion"], d5["loo_contribution"])
# partial: residualize dispersion & loo on difficulty + mean knn, then correlate (rank)
from numpy.linalg import lstsq
def resid(y, Z):
    Z = np.column_stack([np.ones(len(y))] + [stats.rankdata(Z[:,j]) for j in range(Z.shape[1])])
    b,*_ = lstsq(Z, stats.rankdata(y), rcond=None)
    return stats.rankdata(y) - Z@b
Zc = d5[["difficulty","knn_novelty_b_mean"]].to_numpy()
pr = np.corrcoef(resid(d5["dispersion"].to_numpy(), Zc), resid(d5["loo_contribution"].to_numpy(), Zc))[0,1]
print(f"IFBench n={len(d5)}: spearman(dispersion, LOO)={rho:+.3f} p={p:.3f} | partial(|difficulty,mean-knn)={pr:+.3f}")
# HoVer dispersion (33 batches)
Mh = tfidf_matrix(hov_full)
hdisp=[]
for i in range(len(hov_events)):
    rm = Mh[i*3:(i+1)*3]; S=(rm@rm.T).toarray(); iu=np.triu_indices(3,1)
    hdisp.append(float((1-S[iu]).mean()))
# HoVer outcome = minibatch improvement (mbi) as proxy (ΔU too sparse); report both
mbi = np.array([np.mean(t["new_subsample_scores"])-np.mean(t["subsample_scores"]) for t in trace])
rho_h,p_h = spearman(np.array(hdisp), mbi)
print(f"HoVer n=33 (THIN): spearman(dispersion, minibatch-improvement)={rho_h:+.3f} p={p_h:.3f}")

print("\nDONE (all checks). $0 offline — no LM/GEPA runs.")
